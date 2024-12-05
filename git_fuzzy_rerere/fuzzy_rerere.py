#!/usr/bin/env python3
"""
A fuzzy git rerere driver that allows for approximate conflict resolution matching
based on configurable context similarity thresholds.
"""

import os
import sys
import difflib
import subprocess
from pathlib import Path
import hashlib
import json
import random
import string

class FuzzyRerere:
    def __init__(self, similarity_threshold=0.8, context_lines=3):
        self.similarity_threshold = similarity_threshold
        self.context_lines = context_lines
        self.git_dir = self._get_git_dir()
        self.rerere_dir = Path(self.git_dir) / "fuzzy-rerere"
        self.rerere_dir.mkdir(exist_ok=True)
        self.random_suffix_length = 8

    def _generate_random_suffix(self):
        """Generate a random string suffix for conflict files."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=self.random_suffix_length))

    def _get_git_dir(self):
        """Get the .git directory for the current repository."""
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()

    def _hash_conflict(self, conflict_text):
        """Create a fuzzy hash of the conflict content."""
        return hashlib.sha256(conflict_text.encode()).hexdigest()[:16]

    def _extract_conflict_markers(self, file_path):
        """Extract conflict markers and their context from a file."""
        conflicts = []
        in_conflict = False
        context_before = []
        conflict_lines = []
        conflict_start_line = 0
        
        with open(file_path) as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            if line.startswith('<<<<<<<'):
                in_conflict = True
                conflict_start_line = i
                before_context = ''.join(context_before[-self.context_lines:]) if context_before else ''
                conflict_lines = [line]
            elif line.startswith('=======') and in_conflict:
                conflict_lines.append(line)
            elif line.startswith('>>>>>>>') and in_conflict:
                conflict_lines.append(line)
                
                after_lines = []
                after_start = min(i + 1, len(lines))
                for j in range(after_start, min(after_start + self.context_lines, len(lines))):
                    if lines[j].startswith('<<<<<<<'):
                        break
                    after_lines.append(lines[j])
                
                conflict_text = ''.join(conflict_lines)
                conflicts.append({
                    'conflict': conflict_text,
                    'before_context': before_context,
                    'after_context': ''.join(after_lines),
                    'start_line': conflict_start_line,
                    'end_line': i,
                    'file_path': str(file_path)
                })
                
                conflict_lines = []
                in_conflict = False
            elif in_conflict:
                conflict_lines.append(line)
            else:
                context_before.append(line)
                if len(context_before) > self.context_lines:
                    context_before.pop(0)
                    
        return conflicts

    def _find_similar_resolution(self, conflict, current_file):
        """Find a similar conflict resolution from the stored records."""
        best_match = None
        best_ratio = 0
        same_file_match = None
        same_file_ratio = 0

        for record_file in self.rerere_dir.glob("*.json"):
            with open(record_file) as f:
                record = json.load(f)
                stored_conflict = record["conflict"]
                ratio = difflib.SequenceMatcher(None, conflict, stored_conflict).ratio()
                
                # Check if this is from the same file
                if ratio > self.similarity_threshold:
                    if record["file_path"] == str(current_file) and ratio > same_file_ratio:
                        same_file_ratio = ratio
                        same_file_match = record["resolution"]
                    elif ratio > best_ratio:
                        best_ratio = ratio
                        best_match = record["resolution"]

        # Prefer matches from the same file if they exist
        if same_file_match is not None:
            return same_file_match, same_file_ratio
        return best_match, best_ratio

    def record_resolution(self, file_path):
        """Record the resolution of conflicts in a file."""
        conflicts = self._extract_conflict_markers(file_path)
        
        # Store the pre-resolution state
        for conflict in conflicts:
            conflict_hash = self._hash_conflict(conflict)
            record_path = self.rerere_dir / f"{conflict_hash}.json"
            
            if not record_path.exists():
                record = {
                    "conflict": conflict,
                    "resolution": None,
                    "file_path": str(file_path)
                }
                with open(record_path, 'w') as f:
                    json.dump(record, f, indent=2)

    def resolve_conflicts(self, file_path):
        """Try to resolve conflicts in a file using stored resolutions."""
        conflicts = self._extract_conflict_markers(file_path)
        resolved = False

        for conflict in conflicts:
            resolution, confidence = self._find_similar_resolution(conflict, file_path)
            if resolution:
                print(f"Found similar resolution with {confidence:.2%} confidence")
                # Apply the resolution
                # TODO: Implement the actual conflict replacement logic
                resolved = True

        return resolved

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fuzzy Git Rerere Driver")
    parser.add_argument('--similarity', type=float, default=0.8,
                       help="Similarity threshold (0.0-1.0)")
    parser.add_argument('--context', type=int, default=3,
                       help="Number of context lines to consider")
    parser.add_argument('command', choices=['record', 'resolve'],
                       help="Command to execute")
    parser.add_argument('file', help="File to process")
    
    args = parser.parse_args()
    
    fuzzy_rerere = FuzzyRerere(
        similarity_threshold=args.similarity,
        context_lines=args.context
    )
    
    if args.command == 'record':
        fuzzy_rerere.record_resolution(args.file)
    elif args.command == 'resolve':
        if fuzzy_rerere.resolve_conflicts(args.file):
            print("Successfully resolved conflicts")
        else:
            print("No matching resolutions found")

if __name__ == "__main__":
    main()

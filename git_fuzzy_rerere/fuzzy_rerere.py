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

    def _calculate_context_similarity(self, context1_before, context1_after, context2_before, context2_after):
        """Calculate the similarity between two sets of context."""
        before_ratio = difflib.SequenceMatcher(None, context1_before, context2_before).ratio()
        after_ratio = difflib.SequenceMatcher(None, context1_after, context2_after).ratio()
        return (before_ratio + after_ratio) / 2

    def _find_similar_resolution(self, conflict_info):
        """Find a similar conflict resolution from the stored records."""
        matches = []
        current_file = conflict_info['file_path']
        current_conflict = conflict_info['conflict']
        current_line = conflict_info['start_line']

        for record_file in self.rerere_dir.glob("*.json"):
            with open(record_file) as f:
                record = json.load(f)
                
                # First check for exact conflict match
                if record["conflict"] != current_conflict:
                    continue
                
                # Calculate context similarity
                context_similarity = self._calculate_context_similarity(
                    conflict_info['before_context'],
                    conflict_info['after_context'],
                    record.get('before_context', ''),
                    record.get('after_context', '')
                )
                
                # Only consider matches with sufficient context similarity
                if context_similarity >= self.similarity_threshold:
                    matches.append({
                        'resolution': record['resolution'],
                        'context_similarity': context_similarity,
                        'same_file': record['file_path'] == current_file,
                        'line_distance': abs(record.get('start_line', 0) - current_line),
                        'file_path': record['file_path']
                    })

        if not matches:
            return None, 0

        # Sort matches by priority:
        # 1. Same file
        # 2. Context similarity
        # 3. Line number proximity
        matches.sort(key=lambda x: (
            x['same_file'],
            x['context_similarity'],
            -x['line_distance']
        ), reverse=True)

        best_match = matches[0]
        return best_match['resolution'], best_match['context_similarity']

    def _compute_resolution(self, file_path_before, file_path_after, conflict_info):
        """
        Compute the resolution by comparing the file content before and after resolution.
        Returns the resolved content that replaced the conflict.
        """
        with open(file_path_before, 'r') as f:
            before_lines = f.readlines()
        with open(file_path_after, 'r') as f:
            after_lines = f.readlines()

        # Extract the lines that replaced the conflict
        start_line = conflict_info['start_line']
        end_line = conflict_info['end_line']
        
        # The resolution is everything in the after_lines that replaced the conflict
        # Find where the before and after content starts differing
        resolution_lines = []
        i = start_line
        while i < len(after_lines):
            if i >= len(before_lines) or after_lines[i] != before_lines[i]:
                resolution_lines.append(after_lines[i])
            if i > end_line and i < len(before_lines) and after_lines[i] == before_lines[i]:
                break
            i += 1
            
        return ''.join(resolution_lines)

    def record_resolution(self, file_path):
        """Record the resolution of conflicts in a file."""
        # Store the pre-resolution state with conflicts
        conflicts = self._extract_conflict_markers(file_path)
        
        # Create a temporary copy of the file with conflicts
        conflict_file = str(file_path) + ".conflict"
        with open(file_path, 'r') as src, open(conflict_file, 'w') as dst:
            dst.write(src.read())
            
        for conflict in conflicts:
            conflict_hash = self._hash_conflict(conflict['conflict'])
            record_path = self.rerere_dir / f"{conflict_hash}.json"
            
            if not record_path.exists():
                # Wait for the user to resolve the conflict in the original file
                input(f"Please resolve the conflict in {file_path} and press Enter...")
                
                # Compute the resolution
                resolution = self._compute_resolution(conflict_file, file_path, conflict)
                
                record = {
                    "conflict": conflict['conflict'],
                    "before_context": conflict['before_context'],
                    "after_context": conflict['after_context'],
                    "resolution": resolution,
                    "file_path": str(file_path),
                    "start_line": conflict['start_line']
                }
                with open(record_path, 'w') as f:
                    json.dump(record, f, indent=2)
        
        # Clean up temporary file
        os.remove(conflict_file)

    def _apply_resolution(self, file_path, conflict_info, resolution):
        """Apply a resolution to a specific conflict in a file."""
        with open(file_path, 'r') as f:
            content = f.readlines()
            
        # Replace the conflict with the resolution
        content[conflict_info['start_line']:conflict_info['end_line'] + 1] = [resolution]
            
        with open(file_path, 'w') as f:
            f.writelines(content)

    def resolve_conflicts(self, file_path):
        """Try to resolve conflicts in a file using stored resolutions."""
        conflicts = self._extract_conflict_markers(file_path)
        resolved = False

        for conflict_info in conflicts:
            resolution, confidence = self._find_similar_resolution(conflict_info)
            if resolution:
                print(f"Found similar resolution with {confidence:.2%} confidence")
                if confidence >= self.similarity_threshold:
                    self._apply_resolution(file_path, conflict_info, resolution)
                    resolved = True
                    print(f"Applied resolution from {conflict_info['file_path']} "
                          f"at line {conflict_info['start_line']}")

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

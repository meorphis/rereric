#!/usr/bin/env python3
"""
A fuzzy git rerere implementation that allows for approximate conflict resolution matching
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

class Rerereric:
    def __init__(self, similarity_threshold=0.8, context_lines=2, git_dir=None):
        self.similarity_threshold = similarity_threshold
        self.context_lines = context_lines
        self.git_dir = git_dir if git_dir else self._get_git_dir()
        self.rerere_dir = Path(self.git_dir) / "fuzzy-rerere"
        self.rerere_dir.mkdir(exist_ok=True)

    def _hash_record(self, record):
        """Create a hash of the entire conflict record including context."""
        content = (
            record["conflict"] +
            record.get("before_context", "") +
            record.get("after_context", "") +
            str(record.get("start_line", "")) +
            str(record.get("end_line", ""))
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

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
        """Create a hash of the conflict content."""
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
                context_before = []
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
        
        # Only look at files with matching conflict hash
        conflict_hash = self._hash_conflict(current_conflict)
        for record_file in self.rerere_dir.glob(f"{conflict_hash}_*.json"):
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
                        'file_path': record['file_path'],
                        'start_line': record['start_line'],
                        'end_line': record['end_line']
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

    def get_pre_path_from_file_path(self, file_path):
        """Get the path to the pre-resolution state for a file."""
        file_id = str(Path(file_path)).replace('/', '__')
        return self.rerere_dir / f"{file_id}.pre"

    def get_file_path_from_pre_path(self, pre_path):
        """Get the path to the file from the pre-resolution state."""
        file_id = pre_path.stem
        return file_id.replace('__', '/').replace('.pre', '').replace(str(self.rerere_dir) + '/', '')

    def mark_conflicts(self, file_paths):
        """Save the entire file state before conflict resolution."""
        for file_path in file_paths:
            with open(file_path, 'r') as f:
                content = f.read()
            
            pre_path = self.get_pre_path_from_file_path(file_path)

            print(f"Saving pre-resolution state to {pre_path}")

            with open(pre_path, 'w') as f:
                f.write(content)
                
        return True

    def save_resolutions(self):
        """Save resolutions after conflicts have been manually resolved."""
        # Find matching pre-resolution state
        for pre_file in self.rerere_dir.glob("*.pre"):
            file_path = self.get_file_path_from_pre_path(pre_file)

            # Load and check pre-resolution content
            with open(pre_file) as f:
                pre_content = f.readlines()
                
            # Extract conflicts from pre-resolution state
            conflicts = self._extract_conflict_markers(pre_file)
            if not conflicts:
                print(f"No conflicts found in pre-resolution state for {file_path} with content {pre_content}")
                pre_file.unlink()  # Clean up pre file since it has no conflicts
                continue
                
            # Load post-resolution content
            with open(file_path) as f:
                post_content = f.readlines()
                
            # Process each conflict, tracking line offsets
            resolutions = []
            line_offset = 0
            
            for conflict in conflicts:
                # Adjust conflict start/end lines based on previous resolutions
                pre_start = conflict["start_line"]
                post_start = pre_start + line_offset
                pre_end = conflict["end_line"]
                post_end = post_start
                
                # Extract resolution
                post_line = post_start
                pre_line = pre_end + 1

                matches = 0

                while post_line < len(post_content) and pre_line < len(pre_content):
                    # Look for meaningful matching content after the conflict
                    # Try to match next N non-empty lines
                    REQUIRED_MATCHING_LINES = 3

                    if pre_content[pre_line].startswith('<<<<<<<'):
                        break

                    if post_content[post_line] == pre_content[pre_line]:
                        if pre_content[pre_line].strip():
                            matches += 1
                        
                        pre_line += 1

                    else:
                        matches = 0
                        pre_line = pre_end + 1
                        post_end = post_line + 1

                    post_line += 1

                    if matches == REQUIRED_MATCHING_LINES:
                        break
                    
                resolution = ''.join(post_content[post_start:post_end])
                
                # Update line offset for next conflict
                original_conflict_lines = conflict["end_line"] - conflict["start_line"] + 1
                resolution_line_count = post_end - post_start
                line_offset += resolution_line_count - original_conflict_lines
                
                resolutions.append({
                    "conflict": conflict["conflict"],
                    "resolution": resolution,
                    "before_context": conflict["before_context"],
                    "after_context": conflict["after_context"],
                    "start_line": conflict["start_line"],
                    "end_line": conflict["end_line"]
                })
            
            # Save each resolution separately
            for resolution in resolutions:
                # Create unique hash for this specific resolution
                conflict_hash = self._hash_conflict(resolution["conflict"])
                record_hash = self._hash_record(resolution)
                record_path = self.rerere_dir / f"{conflict_hash}_{record_hash}.json"
                
                record = {
                    "file_path": str(file_path),
                    "conflict": resolution["conflict"],
                    "resolution": resolution["resolution"],
                    "before_context": resolution["before_context"],
                    "after_context": resolution["after_context"],
                    "start_line": resolution["start_line"],
                    "end_line": resolution["end_line"]
                }
                with open(record_path, 'w') as f:
                    json.dump(record, f, indent=2)
            
            # Clean up temporary files
            pre_file.unlink()

    def _apply_resolution(self, file_path, conflict_info, resolution):
        """Apply a resolution to a specific conflict in a file."""
        with open(file_path, 'r') as f:
            content = f.readlines()
            
        # Replace the conflict with the resolution
        content[conflict_info['start_line']:conflict_info['end_line'] + 1] = [resolution]
            
        with open(file_path, 'w') as f:
            f.writelines(content)

    def reapply_resolutions(self, file_paths):
        """Try to resolve conflicts in a file using stored resolutions."""
        resolved = []

        for file_path in file_paths:
            conflicts = self._extract_conflict_markers(file_path)
            
            # Process conflicts from bottom to top to maintain line numbers
            for conflict_info in reversed(conflicts):
                resolution, confidence = self._find_similar_resolution(conflict_info)

                if resolution:
                    print(f"Found similar resolution with {confidence:.2%} confidence")
                    if confidence >= self.similarity_threshold:
                        self._apply_resolution(file_path, conflict_info, resolution)
                        resolved.append(file_path)
                        print(f"Applied resolution from {conflict_info['file_path']} "
                            f"at line {conflict_info['start_line']}")

        return resolved

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fuzzy Git Rerere Driver")
    parser.add_argument('--similarity', type=float, default=0.8,
                       help="Similarity threshold (0.0-1.0)")
    parser.add_argument('--context', type=int, default=2,
                       help="Number of context lines to consider")
    parser.add_argument('command', choices=['mark_conflicts', 'save_resolutions', 'reapply_resolutions'],
                       help="Command to execute (pre=save pre-resolution, post=save post-resolution, resolve=apply resolution)")
    parser.add_argument('files', nargs='*', help="Files to process")

    args = parser.parse_args()

    fuzzy_rerere = FuzzyRerere(
        similarity_threshold=args.similarity,
        context_lines=args.context
    )

    if args.command == 'mark_conflicts':
        if fuzzy_rerere.mark_conflicts(args.files):
            print(f"Saved pre-resolution state for {args.files}")
    elif args.command == 'save_resolutions':
        fuzzy_rerere.save_resolutions()
        print(f"Saved post-resolution state")
    elif args.command == 'reapply_resolutions':
        output = fuzzy_rerere.reapply_resolutions(args.files)
        if output:
            print(f"Successfully resolved conflicts in {output}")
        else:
            print("No matching resolutions found")

if __name__ == "__main__":
    main()

from .core import Rerereric

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

    rerereric = Rerereric()

    if args.command == 'mark_conflicts':
        if rerereric.mark_conflicts(args.files, context_lines=args.context):
            print(f"Saved pre-resolution state for {args.files}")
    elif args.command == 'save_resolutions':
        rerereric.save_resolutions(context_lines=args.context)
        print(f"Saved post-resolution state")
    elif args.command == 'reapply_resolutions':
        output = rerereric.reapply_resolutions(
            args.files,
            similarity_threshold=args.similarity,
            context_lines=args.context
        )
        if output:
            print(f"Successfully resolved conflicts in {output}")
        else:
            print("No matching resolutions found")

if __name__ == "__main__":
    main()

# rerereric

rerereric is inspired by [git rerere](https://git-scm.com/book/en/v2/Git-Tools-Rerere). It is a way to cache resolutions to merge conflicts and re-apply those resolutions if they occur again. Unlike `git rerere` it allows fuzzy matching of merge conflicts.

In particular, for two merge conflict to be considered the same:
- They do not need to have occurred in the same file
- They do not need to have occurred on the same line numbers
- The surrounding context does not need to match exactly; instead, you can use the --context and --similarity arguments to specify how many lines of context to look at and how similar it needs to be (as a fraction, relative to the output of difflib)

If a merge conflict has multiple matches in the cache, we prioritize by:
- Looking first at matches with the same filename
- If there are still multiple, looking at how similar the context is
- If there are still multiple, looking at how close the line numbers are

## Installation

```sh
# install from PyPI
pip install https://github.com/meorphis/rerereric
```

## Usage
```
// save the versions of these files that contain the conflict markers
rerereric mark_conflicts file1.ts file2.ts

// [resolve conflicts in these files]

// save the resolutions you applied to a cache (looks at the same files specified in the previous step)
rerereric save_resolutions --context=2

// [conflict later re-emerges, possibly in files with different names]

// read resolutions from the cache and apply them if they match (using different files is ok)
rerereric reapply_resolutions --context=2 --similarity=0.9 file1.ts file3.ts
```
# The Rules of Claude Code

1. First, thoroughly consider the problem, read all relevant files in the codebase, and write out your plan in tasks/todo.md.
2. Your plan should include a list of actionable ToDo items that can be checked off once completed.
3. Before starting any work, contact me and review the plan together.
4. Then begin working through the ToDo items, marking each one as completed when done.
5. At each step, provide a brief explanation of what changes were made.
6. Keep tasks and code changes as simple as possible. We aim to avoid large, complex modifications. All changes should minimize impact on the codebase. Simplicity is the highest priority.
7. Finally, add a “Review” section to the todo.md file summarizing the changes made and including any other relevant information.
8. At each logical milestone, stage and commit your changes with git. Write the commit message in clear, concise Japanese that adheres to the Semantic Commit Message convention.
9. Add any generated caches, build artifacts, or files containing sensitive information to gitignore as needed, and do not commit them to the repository.
10. Always test in a virtual environment such as WSL or Python venv to ensure reproducibility and safety.

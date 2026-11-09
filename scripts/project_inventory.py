"""Inspect tracked Python imports without importing the application or accessing its database."""

import argparse
import ast
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLICATION_DIRECTORIES = {"db", "metrics", "models", "services", "ui"}


def tracked_python_files(root):
    output = subprocess.check_output(["git", "ls-files", "-z", "--", "*.py"], cwd=root)
    return [Path(name) for name in output.decode("utf-8").split("\0") if name]


def module_name(path):
    parts = path.with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def local_imports(tree, module, path, modules):
    """Include local, conditional and function-scoped imports and package initializers."""
    found = set()

    def include(name):
        if name in modules:
            found.add(name)
        parts = name.split(".")
        for index in range(1, len(parts)):
            parent = ".".join(parts[:index])
            if parent in modules and modules[parent].name == "__init__.py":
                found.add(parent)

    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                include(alias.name)
        elif isinstance(node, ast.ImportFrom):
            prefix = node.module or ""
            if node.level:
                parts = package.split(".") if package else []
                prefix = ".".join(
                    parts[: len(parts) - node.level + 1] + ([prefix] if prefix else [])
                )
            include(prefix)
            for alias in node.names:
                include(f"{prefix}.{alias.name}")
    return found - {module}


def command_line_entry(tree):
    for node in tree.body:
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        test = node.test
        if (
            isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        ):
            return True
    return False


def reachable(graph, roots):
    found, pending = set(), list(roots)
    while pending:
        module = pending.pop()
        if module not in graph or module in found:
            continue
        found.add(module)
        pending.extend(graph[module] - found)
    return found


def test_trees(tree):
    """Inspect literal AppTest scripts as source, without executing them."""
    yield tree
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if not re.search(r"(^|\n)\s*(?:from|import)\s", node.value):
                continue
            try:
                yield ast.parse(node.value)
            except SyntaxError:
                # An arbitrary test string need not be a complete Python script.
                continue


def inventory(root=ROOT):
    files = tracked_python_files(root)
    tests = [path for path in files if path.parts[0] == "tests"]
    application = [
        path for path in files if len(path.parts) == 1 or path.parts[0] in APPLICATION_DIRECTORIES
    ]
    tooling = sorted(set(files) - set(application) - set(tests))
    modules = {module_name(path): path for path in application}
    trees = {
        name: ast.parse((root / path).read_text(encoding="utf-8-sig"))
        for name, path in modules.items()
    }
    graph = {
        name: local_imports(trees[name], name, path, modules) for name, path in modules.items()
    }
    cli_roots = sorted(
        name for name, tree in trees.items() if name != "streamlit_app" and command_line_entry(tree)
    )
    app_reachable = reachable(graph, ["streamlit_app"])
    cli_reachable = reachable(graph, cli_roots)
    test_importers = defaultdict(set)
    for path in tests:
        tree = ast.parse((root / path).read_text(encoding="utf-8-sig"))
        for source in test_trees(tree):
            for name in local_imports(source, module_name(path), path, modules):
                test_importers[name].add(path.as_posix())
    test_reachable = reachable(graph, test_importers)
    importers = defaultdict(set)
    for name, dependencies in graph.items():
        for dependency in dependencies:
            importers[dependency].add(name)
    records = []
    for name, path in sorted(modules.items()):
        scope = (
            "application"
            if name in app_reachable
            else "command_line"
            if name in cli_reachable
            else "review"
        )
        records.append(
            dict(
                module=name,
                path=path.as_posix(),
                scope=scope,
                lines=len((root / path).read_text(encoding="utf-8-sig").splitlines()),
                imports=sorted(graph[name]),
                importers=sorted(importers[name]),
                test_importers=sorted(test_importers[name]),
                test_reachable=name in test_reachable,
            )
        )
    return dict(
        baseline_commit=subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True
        ).strip(),
        counts=dict(
            application_python_files=len(application),
            test_python_files=len(tests),
            tooling_python_files=len(tooling),
            application_import_closure=len(app_reachable),
            command_line_only=len(cli_reachable - app_reachable),
            review=len(set(modules) - app_reachable - cli_reachable),
            application_source_lines=sum(record["lines"] for record in records),
        ),
        packages=dict(
            sorted(
                Counter(
                    path.parts[0] if len(path.parts) > 1 else "(root)" for path in application
                ).items()
            )
        ),
        command_line_roots=cli_roots,
        tooling=[path.as_posix() for path in tooling],
        modules=records,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="Print every module, dependency and test importer"
    )
    args = parser.parse_args()
    report = inventory()
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print(f"Baseline: {report['baseline_commit']}")
    for name, count in report["counts"].items():
        print(f"{name}: {count}")
    print("\nOutside the application import closure:")
    for record in report["modules"]:
        if record["scope"] != "application":
            tests = "yes" if record["test_reachable"] else "no"
            print(f"  {record['module']}: {record['scope']}; reachable from tests: {tests}")
    print("\nImport reachability is not runtime coverage or proof that code can be deleted.")


if __name__ == "__main__":
    main()

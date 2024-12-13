import time
import os
import glob
from pathlib import Path
import ast
import sys

def find_python_files():
    """Find all Python files in the project directory and subdirectories"""
    python_files = []
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def check_for_completion():
    """Check all Python files for the completion signal from Agent 1"""
    python_files = find_python_files()
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                if content.strip().endswith("# Agent 1 is done"):
                    # Only accept completion signal in main.py or in the root directory
                    if file_path == './src/main.py' or file_path == './main.py':
                        print(f"\nFound completion signal in {file_path}")
                        return True
                    else:
                        print(f"\nFound completion signal in wrong location: {file_path}")
                        print("Waiting for completion signal in main implementation file...")
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return False

class CodeAnalyzer(ast.NodeVisitor):
    """AST-based code analyzer"""
    def __init__(self):
        self.issues = []

    def visit_import(self, node):
        """Check import statements"""
        self.generic_visit(node)

    def visit_function_def(self, node):
        """Check function definitions"""
        if not node.name.islower():
            self.issues.append(f"Function '{node.name}' should use lowercase naming")
        self.generic_visit(node)

    def visit_class_def(self, node):
        """Check class definitions"""
        if not node.name[0].isupper():
            self.issues.append(f"Class '{node.name}' should use CamelCase naming")
        self.generic_visit(node)

def analyze_file(file_path):
    """Analyze a single Python file for issues"""
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Syntax check
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            issues.append(f"Syntax error in {file_path}: {str(e)}")
            return issues

        # AST-based analysis
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)
        issues.extend([f"{file_path}: {issue}" for issue in analyzer.issues])

        # Check for common issues
        if "import *" in content:
            issues.append(f"{file_path}: Using 'import *' is not recommended")

        # Check for proper socket handling
        if "socket" in content and "close()" not in content:
            issues.append(f"{file_path}: Socket might not be properly closed")

        # Check for proper exception handling
        if "except:" in content and "except Exception:" not in content:
            issues.append(f"{file_path}: Bare 'except:' clause found")

    except Exception as e:
        issues.append(f"Error analyzing {file_path}: {str(e)}")

    return issues

def analyze_and_fix_code():
    """Analyze all Python files for issues"""
    all_issues = []
    python_files = find_python_files()

    print(f"Found {len(python_files)} Python files to analyze")
    for file_path in python_files:
        print(f"Analyzing {file_path}...")
        file_issues = analyze_file(file_path)
        all_issues.extend(file_issues)

    return all_issues

def write_report(issues):
    """Write a detailed report of the analysis"""
    with open("report.txt", "w", encoding='utf-8') as report:
        report.write("Code Analysis Report\n")
        report.write("===================\n\n")
        report.write(f"Analysis completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        if not issues:
            report.write("No issues found in the codebase.\n")
        else:
            report.write(f"Found {len(issues)} issues:\n\n")
            for issue in issues:
                report.write(f"- {issue}\n")

        report.write("\nNote: This analysis was performed by Agent 2 after Agent 1's completion.\n")

def main():
    """Main entry point for the monitoring script"""
    print("Starting monitoring script...")
    print("Watching for Python files and Agent 1's completion signal...")
    print("Note: Will only accept completion signal in main implementation file.")

    last_check_files = set()

    while True:
        try:
            current_files = set(find_python_files())

            # Check for new or modified files
            if current_files != last_check_files:
                print("\nDetected changes in Python files...")
                last_check_files = current_files

            if check_for_completion():
                print("\nAgent 1 has completed their work!")
                print("Starting comprehensive code analysis...")
                issues = analyze_and_fix_code()
                write_report(issues)
                print("\nAnalysis complete. Results have been written to report.txt")
                break

            time.sleep(2)  # Check every 2 seconds

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
            break
        except Exception as e:
            print(f"Error during monitoring: {e}")
            time.sleep(5)  # Wait a bit longer if there's an error

if __name__ == "__main__":
    main()
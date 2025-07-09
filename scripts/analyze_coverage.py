#!/usr/bin/env python3
"""Analyze test coverage and identify gaps.

This script helps identify modules with low test coverage and prioritize
testing efforts based on code importance and coverage metrics.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple


class CoverageAnalyzer:
    """Analyze test coverage data and identify gaps."""
    
    def __init__(self, coverage_file: str = "coverage.json"):
        self.coverage_file = Path(coverage_file)
        self.coverage_data = self.load_coverage()
        
    def load_coverage(self) -> Dict:
        """Load coverage data from JSON file."""
        if not self.coverage_file.exists():
            raise FileNotFoundError(f"Coverage file {self.coverage_file} not found. Run pytest with --cov first.")
        
        with open(self.coverage_file) as f:
            return json.load(f)
    
    def get_module_coverage(self) -> List[Tuple[str, float, int, int]]:
        """Get coverage percentage for each module.
        
        Returns:
            List of (module_path, coverage_percent, statements, missing)
        """
        modules = []
        
        for file_path, file_data in self.coverage_data.get("files", {}).items():
            if file_path.startswith("coda/"):
                summary = file_data.get("summary", {})
                total_statements = summary.get("num_statements", 0)
                covered_statements = summary.get("covered_lines", 0)
                missing_lines = summary.get("missing_lines", 0)
                
                if total_statements > 0:
                    coverage_percent = (covered_statements / total_statements) * 100
                else:
                    coverage_percent = 100.0
                
                modules.append((
                    file_path,
                    coverage_percent,
                    total_statements,
                    missing_lines
                ))
        
        return sorted(modules, key=lambda x: x[1])  # Sort by coverage %
    
    def categorize_modules(self, modules: List[Tuple[str, float, int, int]]) -> Dict[str, List]:
        """Categorize modules by coverage level."""
        categories = {
            "critical": [],    # < 20% coverage
            "low": [],        # 20-50% coverage
            "medium": [],     # 50-80% coverage
            "good": [],       # 80-95% coverage
            "excellent": []   # > 95% coverage
        }
        
        for module, coverage, statements, missing in modules:
            if coverage < 20:
                categories["critical"].append((module, coverage, statements, missing))
            elif coverage < 50:
                categories["low"].append((module, coverage, statements, missing))
            elif coverage < 80:
                categories["medium"].append((module, coverage, statements, missing))
            elif coverage < 95:
                categories["good"].append((module, coverage, statements, missing))
            else:
                categories["excellent"].append((module, coverage, statements, missing))
        
        return categories
    
    def identify_priority_modules(self, modules: List[Tuple[str, float, int, int]]) -> List[Tuple[str, float, int, str]]:
        """Identify high-priority modules for testing based on importance and coverage."""
        priority_patterns = {
            "cli/": "High - User-facing interface",
            "providers/": "High - Core provider functionality",
            "agents/": "High - Agent system core",
            "session/": "High - Session management",
            "tools/": "Medium - Tool execution",
            "observability/": "Medium - Monitoring features",
            "intelligence/": "Medium - Code analysis",
            "web/": "Low - Web UI (separate testing)",
        }
        
        priorities = []
        
        for module, coverage, statements, missing in modules:
            if coverage < 50:  # Only focus on low coverage
                priority = "Low"
                reason = "General module"
                
                for pattern, priority_info in priority_patterns.items():
                    if pattern in module:
                        priority = priority_info.split(" - ")[0]
                        reason = priority_info.split(" - ")[1]
                        break
                
                # Skip __init__.py files with low statement count
                if module.endswith("__init__.py") and statements < 10:
                    continue
                
                priorities.append((module, coverage, statements, f"{priority} - {reason}"))
        
        # Sort by priority (High > Medium > Low) and then by statement count
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        return sorted(priorities, key=lambda x: (priority_order[x[3].split(" - ")[0]], -x[2]))
    
    def generate_report(self):
        """Generate comprehensive coverage report."""
        modules = self.get_module_coverage()
        categories = self.categorize_modules(modules)
        priorities = self.identify_priority_modules(modules)
        
        print("=" * 80)
        print("TEST COVERAGE ANALYSIS REPORT")
        print("=" * 80)
        
        # Overall statistics
        total_modules = len(modules)
        total_statements = sum(m[2] for m in modules)
        total_covered = sum(m[2] * m[1] / 100 for m in modules)
        overall_coverage = (total_covered / total_statements * 100) if total_statements > 0 else 0
        
        print(f"\nOverall Coverage: {overall_coverage:.1f}%")
        print(f"Total Modules: {total_modules}")
        print(f"Total Statements: {total_statements}")
        
        # Coverage distribution
        print("\nCoverage Distribution:")
        print("-" * 40)
        for category, items in categories.items():
            print(f"{category.capitalize()}: {len(items)} modules")
        
        # Critical modules (< 20% coverage)
        if categories["critical"]:
            print("\n🚨 CRITICAL - Modules with < 20% coverage:")
            print("-" * 60)
            for module, coverage, statements, missing in categories["critical"][:10]:
                print(f"{coverage:5.1f}% | {statements:4d} stmts | {module}")
        
        # Priority recommendations
        if priorities:
            print("\n📋 PRIORITY TESTING RECOMMENDATIONS:")
            print("-" * 80)
            print("Coverage | Stmts | Priority | Module")
            print("-" * 80)
            for module, coverage, statements, priority in priorities[:15]:
                print(f"{coverage:5.1f}%   | {statements:4d}  | {priority}")
                print(f"         |       | Module: {module}")
                print("-" * 80)
        
        # Modules with good coverage
        if categories["excellent"]:
            print("\n✅ EXCELLENT - Modules with > 95% coverage:")
            print("-" * 60)
            for module, coverage, statements, missing in categories["excellent"]:
                print(f"{coverage:5.1f}% | {statements:4d} stmts | {module}")
    
    def export_uncovered_lines(self, output_dir: str = "coverage_gaps"):
        """Export detailed uncovered lines for priority modules."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        modules = self.get_module_coverage()
        priorities = self.identify_priority_modules(modules)
        
        for module, coverage, statements, priority in priorities[:5]:  # Top 5 priority modules
            if module in self.coverage_data.get("files", {}):
                file_data = self.coverage_data["files"][module]
                missing_lines = file_data.get("missing_lines", [])
                excluded_lines = file_data.get("excluded_lines", [])
                
                output_file = output_path / f"{module.replace('/', '_')}_gaps.txt"
                with open(output_file, 'w') as f:
                    f.write(f"Coverage Gaps for: {module}\n")
                    f.write(f"Coverage: {coverage:.1f}%\n")
                    f.write(f"Priority: {priority}\n")
                    f.write(f"Total Statements: {statements}\n")
                    f.write(f"Missing Lines: {len(missing_lines)}\n")
                    f.write("=" * 60 + "\n\n")
                    
                    f.write("Missing Line Numbers:\n")
                    f.write(str(missing_lines) + "\n\n")
                    
                    if excluded_lines:
                        f.write("Excluded Lines:\n")
                        f.write(str(excluded_lines) + "\n")
        
        print(f"\nDetailed coverage gaps exported to {output_path}/")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze test coverage and identify gaps"
    )
    parser.add_argument(
        "--coverage-file",
        default="coverage.json",
        help="Path to coverage.json file"
    )
    parser.add_argument(
        "--export-gaps",
        action="store_true",
        help="Export detailed coverage gaps for priority modules"
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=80.0,
        help="Minimum acceptable coverage percentage"
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = CoverageAnalyzer(args.coverage_file)
        analyzer.generate_report()
        
        if args.export_gaps:
            analyzer.export_uncovered_lines()
        
        # Check if coverage meets threshold
        modules = analyzer.get_module_coverage()
        total_statements = sum(m[2] for m in modules)
        total_covered = sum(m[2] * m[1] / 100 for m in modules)
        overall_coverage = (total_covered / total_statements * 100) if total_statements > 0 else 0
        
        if overall_coverage < args.min_coverage:
            print(f"\n❌ Coverage {overall_coverage:.1f}% is below threshold {args.min_coverage}%")
            return 1
        else:
            print(f"\n✅ Coverage {overall_coverage:.1f}% meets threshold {args.min_coverage}%")
            return 0
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
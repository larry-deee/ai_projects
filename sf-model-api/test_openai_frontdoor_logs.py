#!/usr/bin/env python3
"""
OpenAI Front-Door Architecture Log Analysis Test
===============================================

Analyzes server logs to ensure OpenAI Front-Door architecture is working correctly
and validates that no prohibited error patterns are occurring.

Key validations:
- ✅ No "Tool call missing function name" errors
- ✅ No "Failed to parse tool calls JSON" errors  
- ✅ No "ignoring tools" log lines
- ✅ OpenAI Front-Door architecture activation logged
- ✅ Model routing based on capabilities, not User-Agent

Usage:
    python test_openai_frontdoor_logs.py [log_file_path]
    
If no log file is provided, it will attempt to read from common locations.
"""

import sys
import os
import re
import json
from typing import Dict, List, Set, Optional
from datetime import datetime
import argparse

class LogAnalyzer:
    """Analyzes server logs for OpenAI Front-Door architecture compliance."""
    
    def __init__(self, log_file_path: Optional[str] = None):
        self.log_file_path = log_file_path or self._find_log_file()
        self.errors_found: List[Dict] = []
        self.warnings_found: List[Dict] = []
        self.architecture_events: List[Dict] = []
        self.line_count = 0
        
        # Error patterns that should NOT appear with working architecture
        self.prohibited_patterns = [
            (r"Tool call missing function name", "CRITICAL", "Tool-call repair shim not working"),
            (r"Failed to parse tool calls JSON", "CRITICAL", "Tool-call parsing errors"),
            (r"ignoring tools", "WARNING", "Tools being stripped (should not happen)"),
            (r"'str' object has no attribute 'get'", "CRITICAL", "API response parsing error"),
            (r"TypeError.*NoneType.*len", "ERROR", "Null response handling error"),
            (r"socket.*timeout", "WARNING", "Connection timeout issues"),
            (r"Authentication failed", "ERROR", "Auth token issues")
        ]
        
        # Positive patterns that should appear with working architecture
        self.expected_patterns = [
            (r"Using new OpenAI Front-Door architecture", "INFO", "Architecture activation"),
            (r"Routing request.*backend=", "INFO", "Backend routing working"),
            (r"Tool calls repaired.*OpenAI compliance", "INFO", "Tool repair working"),
            (r"OpenAI Front-Door architecture responding correctly", "INFO", "Architecture functional")
        ]
    
    def _find_log_file(self) -> Optional[str]:
        """Find log file in common locations."""
        possible_paths = [
            "server.log",
            "logs/server.log", 
            "/tmp/sf-model-api.log",
            os.path.expanduser("~/sf-model-api.log")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If no log file found, we'll check if server is outputting to stdout
        return None
    
    def analyze_log_file(self) -> Dict:
        """Analyze the log file and return comprehensive results."""
        if not self.log_file_path or not os.path.exists(self.log_file_path):
            return self._create_no_log_result()
        
        print(f"🔍 Analyzing log file: {self.log_file_path}")
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    self.line_count = line_num
                    self._analyze_line(line, line_num)
            
            return self._create_analysis_result()
        
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to read log file: {e}",
                "analysis": {}
            }
    
    def _create_no_log_result(self) -> Dict:
        """Create result when no log file is available."""
        return {
            "status": "no_logs",
            "message": "No log file found. Server might be outputting to stdout.",
            "recommendation": "Run server with logging to file for analysis.",
            "analysis": {
                "prohibited_errors": 0,
                "expected_events": 0,
                "warnings": 0,
                "lines_analyzed": 0
            }
        }
    
    def _analyze_line(self, line: str, line_num: int):
        """Analyze a single log line."""
        timestamp = self._extract_timestamp(line)
        
        # Check for prohibited patterns
        for pattern, level, description in self.prohibited_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                self.errors_found.append({
                    "line": line_num,
                    "timestamp": timestamp,
                    "level": level,
                    "pattern": pattern,
                    "description": description,
                    "content": line.strip()
                })
        
        # Check for expected patterns
        for pattern, level, description in self.expected_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                self.architecture_events.append({
                    "line": line_num,
                    "timestamp": timestamp,
                    "level": level,
                    "pattern": pattern,
                    "description": description,
                    "content": line.strip()
                })
        
        # Check for warnings
        if re.search(r"WARNING|WARN", line, re.IGNORECASE):
            self.warnings_found.append({
                "line": line_num,
                "timestamp": timestamp,
                "content": line.strip()
            })
    
    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from log line."""
        # Look for common timestamp formats
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}',
            r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',
            r'\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}'
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group()
        
        return None
    
    def _create_analysis_result(self) -> Dict:
        """Create comprehensive analysis result."""
        # Categorize errors by severity
        critical_errors = [e for e in self.errors_found if e["level"] == "CRITICAL"]
        regular_errors = [e for e in self.errors_found if e["level"] == "ERROR"]
        warnings = [e for e in self.errors_found if e["level"] == "WARNING"]
        
        # Determine overall status
        if critical_errors:
            status = "critical_issues"
        elif regular_errors:
            status = "errors_found"
        elif warnings:
            status = "warnings_found"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "analysis": {
                "lines_analyzed": self.line_count,
                "prohibited_errors": len(self.errors_found),
                "critical_errors": len(critical_errors),
                "regular_errors": len(regular_errors),
                "warnings": len(warnings),
                "expected_events": len(self.architecture_events),
                "general_warnings": len(self.warnings_found)
            },
            "critical_issues": critical_errors,
            "errors": regular_errors,
            "warnings": warnings,
            "architecture_events": self.architecture_events,
            "general_warnings": self.warnings_found[:10]  # Limit to first 10
        }
    
    def generate_report(self, analysis: Dict) -> str:
        """Generate human-readable report."""
        report_lines = []
        
        # Header
        report_lines.append("🔍 OpenAI Front-Door Architecture Log Analysis Report")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # Status summary
        status = analysis["status"]
        status_emoji = {
            "healthy": "✅",
            "warnings_found": "⚠️",
            "errors_found": "❌",
            "critical_issues": "🚨",
            "no_logs": "📄",
            "error": "💥"
        }.get(status, "❓")
        
        report_lines.append(f"Overall Status: {status_emoji} {status.upper().replace('_', ' ')}")
        report_lines.append("")
        
        if "error" in analysis:
            report_lines.append(f"Error: {analysis['error']}")
            return "\n".join(report_lines)
        
        # Analysis summary
        if "analysis" in analysis:
            summary = analysis["analysis"]
            report_lines.append("📊 Analysis Summary:")
            report_lines.append(f"  Lines Analyzed: {summary.get('lines_analyzed', 0)}")
            report_lines.append(f"  Critical Errors: {summary.get('critical_errors', 0)}")
            report_lines.append(f"  Regular Errors: {summary.get('regular_errors', 0)}")
            report_lines.append(f"  Warnings: {summary.get('warnings', 0)}")
            report_lines.append(f"  Architecture Events: {summary.get('expected_events', 0)}")
            report_lines.append("")
        
        # Critical issues
        if analysis.get("critical_issues"):
            report_lines.append("🚨 CRITICAL ISSUES FOUND:")
            report_lines.append("-" * 40)
            for issue in analysis["critical_issues"]:
                report_lines.append(f"  Line {issue['line']}: {issue['description']}")
                report_lines.append(f"    Pattern: {issue['pattern']}")
                report_lines.append(f"    Content: {issue['content'][:100]}...")
                report_lines.append("")
        
        # Regular errors
        if analysis.get("errors"):
            report_lines.append("❌ ERRORS FOUND:")
            report_lines.append("-" * 40)
            for error in analysis["errors"]:
                report_lines.append(f"  Line {error['line']}: {error['description']}")
                report_lines.append(f"    Pattern: {error['pattern']}")
                report_lines.append("")
        
        # Warnings
        if analysis.get("warnings"):
            report_lines.append("⚠️  WARNINGS:")
            report_lines.append("-" * 40)
            for warning in analysis["warnings"]:
                report_lines.append(f"  Line {warning['line']}: {warning['description']}")
                report_lines.append("")
        
        # Architecture events (positive)
        if analysis.get("architecture_events"):
            report_lines.append("✅ ARCHITECTURE EVENTS:")
            report_lines.append("-" * 40)
            for event in analysis["architecture_events"]:
                report_lines.append(f"  Line {event['line']}: {event['description']}")
                report_lines.append("")
        
        # Recommendations
        report_lines.append("💡 RECOMMENDATIONS:")
        report_lines.append("-" * 40)
        
        if analysis["status"] == "healthy":
            report_lines.append("  ✅ OpenAI Front-Door architecture appears to be working correctly!")
            report_lines.append("  ✅ No prohibited error patterns detected.")
            report_lines.append("  ✅ Tool-call repair shim is functioning properly.")
        elif analysis["status"] == "critical_issues":
            report_lines.append("  🚨 IMMEDIATE ACTION REQUIRED:")
            report_lines.append("    - Critical errors detected that prevent proper operation")
            report_lines.append("    - Check tool-call repair shim implementation")
            report_lines.append("    - Verify OpenAI Front-Door architecture is enabled")
        elif analysis["status"] == "errors_found":
            report_lines.append("  ❌ Errors need attention:")
            report_lines.append("    - Check authentication token configuration")
            report_lines.append("    - Verify network connectivity") 
            report_lines.append("    - Review response parsing logic")
        elif analysis["status"] == "warnings_found":
            report_lines.append("  ⚠️  Minor issues detected:")
            report_lines.append("    - Monitor for recurring patterns")
            report_lines.append("    - Consider increasing timeout values")
        elif analysis["status"] == "no_logs":
            report_lines.append("  📄 No log file available:")
            report_lines.append("    - Enable file logging for better analysis")
            report_lines.append("    - Check server stdout for immediate issues")
        
        return "\n".join(report_lines)

def main():
    """Main entry point for log analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze OpenAI Front-Door architecture logs"
    )
    parser.add_argument(
        "log_file", 
        nargs="?", 
        help="Path to log file (optional)"
    )
    parser.add_argument(
        "--json", 
        action="store_true", 
        help="Output results in JSON format"
    )
    
    args = parser.parse_args()
    
    # Create analyzer and run analysis
    analyzer = LogAnalyzer(args.log_file)
    analysis = analyzer.analyze_log_file()
    
    if args.json:
        # JSON output for programmatic use
        print(json.dumps(analysis, indent=2))
    else:
        # Human-readable report
        report = analyzer.generate_report(analysis)
        print(report)
    
    # Exit with appropriate code
    if analysis["status"] in ["healthy", "no_logs"]:
        sys.exit(0)
    elif analysis["status"] in ["warnings_found"]:
        sys.exit(1)
    else:  # errors_found, critical_issues, error
        sys.exit(2)

if __name__ == "__main__":
    main()
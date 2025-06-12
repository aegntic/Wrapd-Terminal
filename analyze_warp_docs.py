#!/usr/bin/env python3
"""
Analyze the crawled Warp documentation and create a comprehensive summary
"""

import os
import json
from pathlib import Path
from collections import defaultdict
import re

def analyze_docs(docs_dir="warp_docs"):
    """Analyze all crawled documentation files"""
    docs_path = Path(docs_dir)
    
    if not docs_path.exists():
        print(f"Documentation directory {docs_dir} does not exist")
        return
    
    analysis = {
        'total_files': 0,
        'total_size': 0,
        'categories': defaultdict(list),
        'file_structure': {},
        'content_overview': {},
        'urls_crawled': []
    }
    
    # Walk through all markdown files
    for md_file in docs_path.rglob('*.md'):
        analysis['total_files'] += 1
        file_size = md_file.stat().st_size
        analysis['total_size'] += file_size
        
        # Get relative path for categorization
        rel_path = md_file.relative_to(docs_path)
        category = str(rel_path.parent) if rel_path.parent != Path('.') else 'root'
        analysis['categories'][category].append(str(rel_path))
        
        # Extract URL and basic content info
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract URL from first line
                url_match = re.search(r'^# (https://[^\n]+)', content)
                if url_match:
                    url = url_match.group(1)
                    analysis['urls_crawled'].append(url)
                
                # Get content overview
                lines = content.split('\n')
                analysis['content_overview'][str(rel_path)] = {
                    'size_bytes': file_size,
                    'line_count': len(lines),
                    'has_content': '## Content' in content,
                    'word_count': len(content.split())
                }
                
        except Exception as e:
            print(f"Error reading {md_file}: {e}")
    
    return analysis

def create_summary_report(analysis):
    """Create a detailed summary report"""
    report = []
    
    report.append("# Warp Documentation Crawl Summary")
    report.append(f"**Generated on:** {Path().cwd()}")
    report.append("")
    
    # Overview
    report.append("## Overview")
    report.append(f"- **Total files crawled:** {analysis['total_files']}")
    report.append(f"- **Total size:** {analysis['total_size']:,} bytes ({analysis['total_size']/1024/1024:.2f} MB)")
    report.append(f"- **Unique URLs:** {len(set(analysis['urls_crawled']))}")
    report.append("")
    
    # Categories
    report.append("## Documentation Categories")
    for category, files in sorted(analysis['categories'].items()):
        report.append(f"### {category.replace('_', ' ').title()}")
        report.append(f"- **File count:** {len(files)}")
        for file in sorted(files)[:5]:  # Show first 5 files
            report.append(f"  - {file}")
        if len(files) > 5:
            report.append(f"  - ... and {len(files) - 5} more files")
        report.append("")
    
    # Largest files
    report.append("## Largest Files")
    largest_files = sorted(
        analysis['content_overview'].items(),
        key=lambda x: x[1]['size_bytes'],
        reverse=True
    )[:10]
    
    for filename, info in largest_files:
        report.append(f"- **{filename}**: {info['size_bytes']:,} bytes, {info['word_count']:,} words")
    report.append("")
    
    # URL samples
    report.append("## Sample URLs Crawled")
    unique_urls = list(set(analysis['urls_crawled']))[:20]
    for url in sorted(unique_urls):
        report.append(f"- {url}")
    if len(unique_urls) > 20:
        report.append(f"- ... and {len(set(analysis['urls_crawled'])) - 20} more URLs")
    
    return '\n'.join(report)

def main():
    print("Analyzing crawled Warp documentation...")
    analysis = analyze_docs()
    
    if analysis:
        # Save analysis as JSON
        with open('warp_docs_analysis.json', 'w') as f:
            # Convert defaultdict to regular dict for JSON serialization
            analysis_json = dict(analysis)
            analysis_json['categories'] = dict(analysis_json['categories'])
            json.dump(analysis_json, f, indent=2)
        
        # Create summary report
        summary = create_summary_report(analysis)
        with open('warp_docs_summary.md', 'w') as f:
            f.write(summary)
        
        print("Analysis complete!")
        print(f"- Total files: {analysis['total_files']}")
        print(f"- Total size: {analysis['total_size']/1024/1024:.2f} MB")
        print(f"- Categories: {len(analysis['categories'])}")
        print("- Files saved: warp_docs_analysis.json, warp_docs_summary.md")
        
        # Print quick overview
        print("\nQuick Overview:")
        for category, files in sorted(analysis['categories'].items()):
            print(f"  {category}: {len(files)} files")

if __name__ == "__main__":
    main()
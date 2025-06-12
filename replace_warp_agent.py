#!/usr/bin/env python3
"""
Comprehensive find-and-replace script to replace:
- Every instance of "warp" with "wrapd" (all variations)
- Every instance of "agent" with "aegnt" (all variations)  
- "agentic" with "aegntic"
"""

import os
import shutil
import re
from pathlib import Path
from collections import defaultdict

class WarpAgentReplacer:
    def __init__(self, docs_dir="warp_docs"):
        self.docs_dir = Path(docs_dir)
        self.backup_dir = Path(f"{docs_dir}_backup")
        self.replacement_stats = defaultdict(int)
        self.files_processed = 0
        self.files_modified = 0
        
        # Define replacement patterns in order (agentic first to avoid conflicts)
        self.replacements = [
            # Handle "agentic" first before "agent"
            (r'\bagentic\b', 'aegntic'),
            (r'\bAgentic\b', 'Aegntic'),
            (r'\bAGENTIC\b', 'AEGNTIC'),
            
            # Agent variations
            (r'\bagent\b', 'aegnt'),
            (r'\bAgent\b', 'Aegnt'),
            (r'\bAGENT\b', 'AEGNT'),
            (r'\bagents\b', 'aegnts'),
            (r'\bAgents\b', 'Aegnts'),
            (r'\bAGENTS\b', 'AEGNTS'),
            (r'\bagent\'s\b', 'aegnt\'s'),
            (r'\bAgent\'s\b', 'Aegnt\'s'),
            (r'\bAGENT\'S\b', 'AEGNT\'S'),
            
            # Warp variations - handle compound words and variations
            (r'\bwarp\b', 'wrapd'),
            (r'\bWarp\b', 'Wrapd'),
            (r'\bWARP\b', 'WRAPD'),
            (r'\bwarps\b', 'wrapds'),
            (r'\bWarps\b', 'Wrapds'),
            (r'\bWARPS\b', 'WRAPDS'),
            (r'\bwarp\'s\b', 'wrapd\'s'),
            (r'\bWarp\'s\b', 'Wrapd\'s'),
            (r'\bWARP\'S\b', 'WRAPD\'S'),
            
            # Compound words and variations
            (r'\bwarpify\b', 'wrapdify'),
            (r'\bWarpify\b', 'Wrapdify'),
            (r'\bWARPIFY\b', 'WRAPDIFY'),
            (r'\bwarping\b', 'wrapdping'),
            (r'\bWarping\b', 'Wrapdping'),
            (r'\bWARPING\b', 'WRAPDPING'),
            (r'\bwarped\b', 'wrapdped'),
            (r'\bWarped\b', 'Wrapdped'),
            (r'\bWARPED\b', 'WRAPDPED'),
            
            # Handle hyphenated words
            (r'warp-', 'wrapd-'),
            (r'Warp-', 'Wrapd-'),
            (r'WARP-', 'WRAPD-'),
            
            # Handle URLs and paths (be comprehensive as requested)
            (r'docs\.warp\.dev', 'docs.wrapd.dev'),
            (r'warp\.dev', 'wrapd.dev'),
            (r'/warp/', '/wrapd/'),
        ]
    
    def create_backup(self):
        """Create backup of original documentation"""
        if self.backup_dir.exists():
            print(f"Removing existing backup at {self.backup_dir}")
            shutil.rmtree(self.backup_dir)
        
        print(f"Creating backup: {self.docs_dir} -> {self.backup_dir}")
        shutil.copytree(self.docs_dir, self.backup_dir)
        print("✅ Backup created successfully")
    
    def get_all_md_files(self):
        """Get all .md files in the documentation directory"""
        return list(self.docs_dir.rglob('*.md'))
    
    def apply_replacements(self, content):
        """Apply all replacements to content and track statistics"""
        original_content = content
        modified = False
        
        for pattern, replacement in self.replacements:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                # Count replacements made
                matches = len(re.findall(pattern, content))
                self.replacement_stats[f"{pattern} -> {replacement}"] += matches
                content = new_content
                modified = True
        
        return content, modified
    
    def process_file(self, file_path):
        """Process a single markdown file"""
        try:
            # Read file with UTF-8 encoding
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Apply replacements
            modified_content, was_modified = self.apply_replacements(original_content)
            
            # Write back if modified
            if was_modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                self.files_modified += 1
                print(f"✅ Modified: {file_path.relative_to(self.docs_dir)}")
            else:
                print(f"⚪ No changes: {file_path.relative_to(self.docs_dir)}")
            
            self.files_processed += 1
            return True
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return False
    
    def generate_report(self):
        """Generate summary report of changes made"""
        print("\n" + "="*60)
        print("📊 REPLACEMENT SUMMARY REPORT")
        print("="*60)
        print(f"Files processed: {self.files_processed}")
        print(f"Files modified: {self.files_modified}")
        print(f"Files unchanged: {self.files_processed - self.files_modified}")
        
        print("\n🔄 Replacement Statistics:")
        total_replacements = 0
        for pattern_replacement, count in sorted(self.replacement_stats.items()):
            if count > 0:
                print(f"  {pattern_replacement}: {count} replacements")
                total_replacements += count
        
        print(f"\n📈 Total replacements made: {total_replacements}")
        
        if total_replacements > 0:
            print(f"\n✅ Successfully replaced all instances of 'warp' -> 'wrapd' and 'agent' -> 'aegnt'")
            print(f"📁 Original files backed up to: {self.backup_dir}")
        else:
            print("\n⚠️  No replacements were made - files may already be processed")
    
    def run(self):
        """Execute the complete replacement operation"""
        print("🚀 Starting comprehensive warp->wrapd and agent->aegnt replacement")
        print(f"📂 Processing directory: {self.docs_dir}")
        
        # Create backup
        self.create_backup()
        
        # Get all markdown files
        md_files = self.get_all_md_files()
        print(f"\n📄 Found {len(md_files)} markdown files to process")
        
        # Process each file
        print("\n🔄 Processing files...")
        for file_path in md_files:
            self.process_file(file_path)
        
        # Generate report
        self.generate_report()

def main():
    replacer = WarpAgentReplacer()
    replacer.run()

if __name__ == "__main__":
    main()
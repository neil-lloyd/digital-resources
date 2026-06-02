#!/usr/bin/env python3
"""
Quarto pre-render script to generate language-specific .qmd files.
Place this file as _pre-render.py in your project root.
"""

import sys
import re
from pathlib import Path

# Configuration - CUSTOMIZE THESE
LANGUAGES = ["R", "Python", "Stata", "Julia"]
SOURCE_FILE = "multi-language-test-4.qmd"

def extract_yaml_and_content(qmd_path):
    """Extract YAML header and content from .qmd file."""
    with open(qmd_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract YAML (between --- markers)
    yaml_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if yaml_match:
        yaml_content = yaml_match.group(1)
        body_content = yaml_match.group(2)
    else:
        yaml_content = ""
        body_content = content
    
    return yaml_content, body_content

def get_available_languages(content):
    """Detect which languages are present in the content by looking for ## Language headers."""
    available = set()
    lines = content.split('\n')
    
    for line in lines:
        # Look for language headers like ## R, ## Python, etc.
        header_match = re.match(r'^##\s+(.+)$', line.strip())
        if header_match:
            lang = header_match.group(1).strip()
            # Check if it matches one of our configured languages
            if lang in LANGUAGES:
                available.add(lang)
    
    return available

def filter_content_by_language(content, target_lang):
    """
    Filter content to keep only code blocks for the target language.
    Removes tabsets and keeps only the target language code.
    """
    lines = content.split('\n')
    filtered_lines = []
    in_tabset = False
    in_target_block = False
    skip_until_next_header = False
    tabset_depth = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Remove statasetup block for R and Python (keep for Stata)
        if '```{r statasetup}' in line.lower():
            # Skip this entire code block
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith('```') and len(lines[i].strip()) == 3:
                    i += 1
                    break
                i += 1
            continue
        
        # Detect tabset start
        if ':::{.panel-tabset' in line or '::: {.panel-tabset' in line:
            in_tabset = True
            tabset_depth += 1
            i += 1
            continue
        
        # Detect tabset end
        if in_tabset and line.strip() == ':::':
            tabset_depth -= 1
            if tabset_depth == 0:
                in_tabset = False
                in_target_block = False
                skip_until_next_header = False
            i += 1
            continue
        
        # Inside tabset
        if in_tabset:
            # Check for language header (## R, ## Python, etc.)
            header_match = re.match(r'^##\s+(.+)$', line.strip())
            if header_match:
                lang_name = header_match.group(1).strip()
                
                if lang_name == target_lang:
                    in_target_block = True
                    skip_until_next_header = False
                else:
                    in_target_block = False
                    skip_until_next_header = True
                i += 1
                continue
            
            # Include content only if we're in the target block
            if in_target_block and not skip_until_next_header:
                filtered_lines.append(line)
        else:
            # Outside tabset, include all content
            filtered_lines.append(line)
        
        i += 1
    
    return '\n'.join(filtered_lines)

def create_language_specific_qmd(yaml_content, body_content, language):
    """Create a language-specific .qmd file."""
    # Filter content for this language
    filtered_content = filter_content_by_language(body_content, language)
    
    # Modify YAML to only include PDF format
    yaml_lines = yaml_content.split('\n')
    new_yaml = []
    in_format = False
    skip_section = False
    title_found = False
    
    for line in yaml_lines:
        # Add subtitle after title
        if line.strip().startswith('title:') and not title_found:
            new_yaml.append(line)
            new_yaml.append(f'subtitle: "with {language} code"')
            title_found = True
            continue
        
        # Start of format section
        if line.strip().startswith('format:'):
            in_format = True
            new_yaml.append('format:')
            new_yaml.append('  pdf:')
            new_yaml.append('    toc: true')
            skip_section = True
            continue
        
        # End of format section (line with no indent or different key)
        if in_format and line.strip() and not line.startswith(' '):
            in_format = False
            skip_section = False
        
        # Skip everything inside format section (we already added pdf)
        if skip_section:
            continue
          
        # Set optimized, language-specific engines
        if line.strip().startswith('engine:') and language == "R":
            new_yaml.append('engine: knitr')
            continue
        if line.strip().startswith('engine:') and language == "Stata":
            new_yaml.append('jupyter: nbstata')
            continue
        if line.strip().startswith('engine:') and language == "Python":
            new_yaml.append('jupyter: python3')
            continue
        if line.strip().startswith('engine:') and language == "Julia":
            new_yaml.append('engine: julia')
            continue
          
        # Keep all other YAML lines
        new_yaml.append(line)

        
    
    # Create output directory
    lang_dir = Path(language)
    lang_dir.mkdir(parents=True, exist_ok=True)
    
    # Create new .qmd file
    base_name = Path(SOURCE_FILE).stem
    output_qmd = lang_dir / f"{base_name}-{language}.qmd"
    
    with open(output_qmd, 'w', encoding='utf-8') as f:
        f.write('---\n')
        f.write('\n'.join(new_yaml))
        f.write('\n---\n')
        f.write(filtered_content)
    
    return output_qmd

def main():
    """Main execution function."""
    # Check if source file exists
    if not Path(SOURCE_FILE).exists():
        print(f"Source file {SOURCE_FILE} not found!", file=sys.stderr)
        return
    
    print(f"Generating language-specific .qmd files for {SOURCE_FILE}...")
    
    # Extract YAML and content
    yaml_content, body_content = extract_yaml_and_content(SOURCE_FILE)
    
    # Detect which languages are actually present in the document
    available_languages = get_available_languages(body_content)
    
    if not available_languages:
        print("No language headers (## R, ## Python, etc.) found in the document.")
        return
    
    print(f"Found languages: {', '.join(sorted(available_languages))}")
    
    # Generate .qmd files only for languages present in the document
    for language in sorted(available_languages):
        print(f"\nProcessing {language}...")
        
        # Create language-specific .qmd
        output_qmd = create_language_specific_qmd(
            yaml_content, 
            body_content, 
            language
        )
        
        print(f"  ✓ Created: {output_qmd}")
    
    print(f"\n✓ All language-specific .qmd files generated!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Quarto pre-render script to generate language-specific .qmd files
for all files in the folder ending with '-multi.qmd'.
"""

import sys
import re
from pathlib import Path

# Configuration
LANGUAGES = ["R", "Python", "Stata", "Julia"]

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
        header_match = re.match(r'^##\s+(.+)$', line.strip())
        if header_match:
            lang = header_match.group(1).strip()
            if lang in LANGUAGES:
                available.add(lang)
    return available

def filter_content_by_language(content, target_lang):
    """Filter content to keep only code blocks for the target language."""
    lines = content.split('\n')
    filtered_lines = []
    in_tabset = False
    in_target_block = False
    skip_until_next_header = False
    tabset_depth = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if '```{r multisetup}' in line.lower():
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith('```') and len(lines[i].strip()) == 3:
                    i += 1
                    break
                i += 1
            continue
        
        if ':::{.panel-tabset' in line or '::: {.panel-tabset' in line:
            in_tabset = True
            tabset_depth += 1
            i += 1
            continue
        
        if in_tabset and line.strip() == ':::':
            tabset_depth -= 1
            if tabset_depth == 0:
                in_tabset = False
                in_target_block = False
                skip_until_next_header = False
            i += 1
            continue
        
        if in_tabset:
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
            
            if in_target_block and not skip_until_next_header:
                filtered_lines.append(line)
        else:
            filtered_lines.append(line)
        
        i += 1
    
    return '\n'.join(filtered_lines)

def create_language_specific_qmd(source_file, yaml_content, body_content, language):
    """Create a language-specific .qmd file."""
    filtered_content = filter_content_by_language(body_content, language)
    
    yaml_lines = yaml_content.split('\n')
    new_yaml = []
    in_format = False
    skip_section = False
    title_found = False

    for line in yaml_lines:
        if line.strip().startswith('title:') and not title_found:
            new_yaml.append(line)
            new_yaml.append(f'subtitle: "with {language} code"')
            title_found = True
            continue
        
        if line.strip().startswith('format:'):
            in_format = True
            new_yaml.append('format:')
            new_yaml.append('  pdf:')
            new_yaml.append('    toc: true')
            skip_section = True
            continue
        
        if in_format and line.strip() and not line.startswith(' '):
            in_format = False
            skip_section = False
        
        if skip_section:
            continue
        
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
        
        new_yaml.append(line)

    # Create output directory
    lang_dir = Path(language)
    lang_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = Path(source_file).stem.replace('-multi', '')
    output_qmd = lang_dir / f"{base_name}-{language}.qmd"
    
    with open(output_qmd, 'w', encoding='utf-8') as f:
        f.write('---\n')
        f.write('\n'.join(new_yaml))
        f.write('\n---\n')
        f.write(filtered_content)
    
    return output_qmd

def main():
    """Main execution function."""
    multi_files = sorted(Path('.').glob('*-multi.qmd'))
    if not multi_files:
        print("No files ending with '-multi.qmd' found in the folder.")
        return

    for source_file in multi_files:
        print(f"\nProcessing file: {source_file.name}")

        yaml_content, body_content = extract_yaml_and_content(source_file)
        available_languages = get_available_languages(body_content)

        if not available_languages:
            print(f"  ⚠ No language headers found in {source_file.name}. Skipping.")
            continue

        print(f"  Found languages: {', '.join(sorted(available_languages))}")
        for language in sorted(available_languages):
            print(f"    → Generating {language} version...")
            output_qmd = create_language_specific_qmd(
                source_file,
                yaml_content,
                body_content,
                language
            )
            print(f"      ✓ Created: {output_qmd}")

    print("\n✓ All multi-language .qmd files processed successfully!")

if __name__ == "__main__":
    main()

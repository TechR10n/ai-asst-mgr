# ai-asst-mgr Development Wiki

These markdown files are designed to be uploaded to the GitHub Wiki at:
https://github.com/TechR10n/ai-asst-mgr/wiki

## Uploading to GitHub Wiki

### Method 1: Manual Upload (Recommended)

1. Go to https://github.com/TechR10n/ai-asst-mgr/wiki
2. Click "New Page" for each wiki page
3. Copy the content from each `.md` file
4. Use the filename (without `.md`) as the page title
5. Save the page

### Method 2: Clone Wiki Repository

GitHub wikis are actually git repositories:

```bash
# Clone the wiki
git clone https://github.com/TechR10n/ai-asst-mgr.wiki.git

# Copy wiki files
cp wiki/*.md ai-asst-mgr.wiki/

# Commit and push
cd ai-asst-mgr.wiki
git add .
git commit -m "Add development wiki pages"
git push origin master
```

### Method 3: Script (Automated)

```bash
# Create a script to automate wiki upload
# scripts/upload_wiki.sh

#!/bin/bash
set -e

# Clone wiki
git clone https://github.com/TechR10n/ai-asst-mgr.wiki.git /tmp/wiki

# Copy files
cp wiki/*.md /tmp/wiki/

# Push
cd /tmp/wiki
git add .
git commit -m "Update wiki pages"
git push origin master

# Cleanup
rm -rf /tmp/wiki
```

## Wiki Pages

Current wiki pages:

1. **Home.md** - Wiki homepage
2. **Development-Setup.md** - Setting up dev environment
3. **Development-Workflow.md** - Branch strategy and PR process
4. **GitHub-Setup-Scripts.md** - Automation scripts for project setup

## Adding New Wiki Pages

1. Create `.md` file in `wiki/` directory
2. Follow existing format and structure
3. Update `Home.md` with link to new page
4. Upload to GitHub Wiki
5. Link from other relevant wiki pages

## Wiki vs. Docs

**Wiki** (`wiki/` → GitHub Wiki):
- For **contributors** and **maintainers**
- Building and developing ai-asst-mgr
- Internal architecture and design
- Development processes

**Docs** (`docs/` → Published with package):
- For **end users**
- Using ai-asst-mgr
- CLI commands and configuration
- Troubleshooting for users

## Local Preview

To preview wiki pages locally:

```bash
# Using Python markdown
pip install markdown
python -m markdown wiki/Home.md > /tmp/wiki.html
open /tmp/wiki.html

# Or use a markdown viewer
# VS Code: Install "Markdown Preview Enhanced" extension
# Vim: :MarkdownPreview
```

## Style Guide

### Formatting

- Use GitHub Flavored Markdown
- Use `##` for main sections
- Use `###` for subsections
- Use code blocks with language specifiers
- Use tables for structured data

### Internal Links

Link to other wiki pages using double brackets:

```markdown
See [[Development Setup]] for details.
```

This creates a link to the "Development Setup" wiki page.

### External Links

Use standard markdown links:

```markdown
[Issue Tracker](https://github.com/TechR10n/ai-asst-mgr/issues)
```

### Code Examples

Always specify language for syntax highlighting:

````markdown
```bash
git commit -m "feat: add feature"
```

```python
def hello():
    print("Hello, World!")
```
````

## Maintenance

- Keep wiki pages up to date with codebase changes
- Review wiki pages during release process
- Archive outdated information
- Link to relevant issues and PRs

## See Also

- [GitHub Wiki Documentation](https://docs.github.com/en/communities/documenting-your-project-with-wikis)
- [GitHub Flavored Markdown](https://github.github.com/gfm/)
- [[Development Setup]]
- [[Development Workflow]]

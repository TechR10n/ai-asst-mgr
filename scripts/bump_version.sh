#!/usr/bin/env bash
# Bump version and create release tag
# Usage: ./scripts/bump_version.sh [major|minor|patch|<version>]

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep -Po '(?<=^version = ")[^"]*' pyproject.toml)
echo "Current version: $CURRENT_VERSION"

# Parse version components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Determine new version
if [ "$#" -eq 0 ]; then
    echo "Usage: $0 [major|minor|patch|<version>]"
    echo ""
    echo "Examples:"
    echo "  $0 patch     # 0.1.0 → 0.1.1"
    echo "  $0 minor     # 0.1.0 → 0.2.0"
    echo "  $0 major     # 0.1.0 → 1.0.0"
    echo "  $0 0.2.0     # Set specific version"
    exit 1
fi

BUMP_TYPE=$1

case $BUMP_TYPE in
    major)
        NEW_VERSION="$((MAJOR + 1)).0.0"
        ;;
    minor)
        NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
        ;;
    patch)
        NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
        ;;
    *)
        # Validate version format
        if [[ ! $BUMP_TYPE =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo -e "${RED}Error: Invalid version format '$BUMP_TYPE'${NC}"
            echo "Version must be in format: major.minor.patch (e.g., 0.1.0)"
            exit 1
        fi
        NEW_VERSION=$BUMP_TYPE
        ;;
esac

echo "New version: $NEW_VERSION"
echo ""

# Confirm
read -p "Bump version from $CURRENT_VERSION to $NEW_VERSION? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Update pyproject.toml
echo "Updating pyproject.toml..."
sed -i.bak "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
rm pyproject.toml.bak

echo -e "${GREEN}✓${NC} Updated pyproject.toml"

# Commit version bump
git add pyproject.toml
git commit -m "chore: bump version to $NEW_VERSION"

echo -e "${GREEN}✓${NC} Committed version bump"

# Create tag
TAG="v$NEW_VERSION"
git tag -a "$TAG" -m "Release $TAG"

echo -e "${GREEN}✓${NC} Created tag: $TAG"
echo ""

# Instructions
echo "========================================="
echo "Version bumped to $NEW_VERSION"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Push commits: git push origin main"
echo "  2. Push tag:     git push origin $TAG"
echo ""
echo "The release workflow will automatically:"
echo "  • Run tests and quality checks"
echo "  • Build wheel and source distribution"
echo "  • Generate changelog from commits"
echo "  • Create GitHub release with artifacts"
echo "  • Update CHANGELOG.md"
echo ""
echo "View release at:"
echo "https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:\/]\(.*\)\.git/\1/')/releases/tag/$TAG"
echo ""

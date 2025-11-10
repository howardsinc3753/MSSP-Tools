# Contributing to FortiFlex MSSP Toolkit

Thank you for your interest in contributing! This document provides guidelines for submitting bugs, feature requests, and pull requests.

---

## 🐛 How to Report a Bug

Found a bug? Help us fix it!

### Step 1: Check Existing Issues
Before creating a new issue, please check:
- **[Known Issues](BUGFIX_USE_CASES.md)** - Check if your issue is already documented
- **[GitHub Issues](https://github.com/howardsinc3753/MSSP-Tools/issues)** - Search for similar reports

### Step 2: Create a Bug Report

1. **Go to:** https://github.com/howardsinc3753/MSSP-Tools/issues
2. **Click:** "New Issue"
3. **Title:** Use a clear, descriptive title
   - ✅ Good: "Use Case 1: Points calculation fails with nested response"
   - ❌ Bad: "Script broken"

4. **Include the following information:**

#### Required Information
```
**Tool:** FortiFlex MSSP Toolkit

**Script/File:**
- Which script? (e.g., use_case_1_customer_onboarding.py)
- Which use case? (1-7)

**Description:**
[Clear description of the issue]

**Steps to Reproduce:**
1. Configure credentials with...
2. Run command...
3. See error...

**Expected Behavior:**
[What should have happened]

**Actual Behavior:**
[What actually happened]

**Environment:**
- Python version: (run `python --version`)
- Operating System: (Windows/Linux/macOS)
- FortiFlex API version: (if known)
- Toolkit version: (see VERSION in README)

**Error Messages:**
```
[Paste full error output here]
⚠️ IMPORTANT: Remove any credentials, API keys, or sensitive data!
```

**Additional Context:**
- Screenshots (if applicable)
- Configuration file format (with credentials removed)
- Any recent changes to your environment
```

### Example Bug Report

```markdown
**Tool:** FortiFlex MSSP Toolkit

**Script/File:** examples/use_case_1_customer_onboarding.py

**Description:**
When running cost estimation with --dry-run, the script crashes with a KeyError
on the points calculation response.

**Steps to Reproduce:**
1. Configure credentials.json with valid API credentials
2. Run: `python examples/use_case_1_customer_onboarding.py --dry-run`
3. Error occurs during cost calculation for FortiGate-60F

**Expected Behavior:**
Should display cost estimation without creating resources

**Actual Behavior:**
Script crashes with:
```
KeyError: 'points' is a dict, expected float
```

**Environment:**
- Python version: 3.9.7
- Operating System: Windows 11
- FortiFlex API version: v2 (25.1.0)
- Toolkit version: 1.0.0

**Error Messages:**
```
Traceback (most recent call last):
  File "examples/use_case_1_customer_onboarding.py", line 234, in main
    daily_cost = result['points'] * quantity
TypeError: unsupported operand type(s) for *: 'dict' and 'int'
```

**Additional Context:**
This worked last week. API response format may have changed.
```

---

## 💡 How to Request a Feature

Have an idea for improvement?

### Step 1: Check Existing Requests
Search [GitHub Issues](https://github.com/howardsinc3753/MSSP-Tools/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement) for similar requests.

### Step 2: Create a Feature Request

1. **Go to:** https://github.com/howardsinc3753/MSSP-Tools/issues
2. **Click:** "New Issue"
3. **Add label:** "enhancement"
4. **Include:**

```markdown
**Feature Request:** [Clear, concise title]

**Use Case:**
[Why is this needed? What problem does it solve?]

**Proposed Solution:**
[How should this work?]

**Example:**
[Code example or workflow showing the feature in action]

**Alternatives Considered:**
[Other approaches you've thought about]

**Additional Context:**
[Any other relevant information]
```

---

## 🔧 How to Submit a Pull Request

Want to contribute code? Awesome!

### Prerequisites
- Fork the repository: https://github.com/howardsinc3753/MSSP-Tools
- Clone your fork locally
- Create a new branch for your changes

### Step 1: Set Up Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/MSSP-Tools.git
cd MSSP-Tools/FortiFlex-Dev-Package/fortiflex-mssp-toolkit

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create a new branch
git checkout -b feature/your-feature-name
```

### Step 2: Make Your Changes

**Code Guidelines:**
- Follow existing code style (PEP 8 for Python)
- Add comments for complex logic
- Include error handling
- Remove any credentials or sensitive data
- Test your changes thoroughly

**Documentation:**
- Update relevant documentation files
- Add docstrings to new functions
- Update README.md if adding new features
- Add examples if applicable

### Step 3: Test Your Changes

```bash
# Run your modified script
python examples/your_modified_script.py

# Test with --dry-run flags where available
python examples/use_case_1_customer_onboarding.py --dry-run

# Verify no credentials in code
grep -r "YOUR_ACTUAL_CREDENTIAL" .
```

### Step 4: Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a clear message
git commit -m "Add feature: Brief description of change

- Detailed explanation of what changed
- Why the change was needed
- Any breaking changes or migration notes"
```

**Commit Message Format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Example:**
```
fix: Correct points calculation in use case 1

- Updated to handle nested points response format from API v2
- Added error handling for missing 'current' field
- Updated documentation with API change notes

Fixes #42
```

### Step 5: Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name
```

Then:
1. Go to https://github.com/howardsinc3753/MSSP-Tools
2. Click "Compare & pull request"
3. Fill out the PR template:

```markdown
## Description
[Clear description of what this PR does]

## Related Issue
Fixes #[issue number]

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## How Has This Been Tested?
[Describe testing performed]
- [ ] Tested with real FortiFlex API
- [ ] Tested in development environment
- [ ] Added/updated tests

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-reviewed my own code
- [ ] Commented complex code sections
- [ ] Updated relevant documentation
- [ ] No credentials or sensitive data in code
- [ ] Tested changes thoroughly
- [ ] All tests pass

## Screenshots (if applicable)
[Add screenshots showing the change]

## Additional Notes
[Any other information reviewers should know]
```

### Step 6: Code Review Process

- Maintainers will review your PR
- Address any requested changes
- Once approved, your PR will be merged!

---

## 🧪 Testing Guidelines

### Before Submitting
- [ ] Test with valid credentials in development environment
- [ ] Test error handling (invalid credentials, network errors)
- [ ] Verify output format matches documentation
- [ ] Check for any hardcoded values
- [ ] Remove debug print statements
- [ ] Verify credentials.json is gitignored

### Test Checklist
```bash
# Authentication
python testing/test_authentication.py

# Program discovery
python testing/discover_program.py

# Use case tests
python examples/use_case_6_multi_tenant_operations.py  # Safe read-only
python examples/consumption_report_v2.py --days 7      # Safe read-only

# Dry run tests
python examples/use_case_1_customer_onboarding.py --dry-run
```

---

## 📝 Documentation Standards

When updating documentation:

1. **Use clear, concise language**
2. **Include code examples** for new features
3. **Update version history** in relevant files
4. **Cross-reference** related documentation
5. **Add warnings** for breaking changes

### Documentation Files to Update
- `README.md` - Main toolkit documentation
- `EXAMPLES_SUMMARY.md` - Use case summaries
- `BUGFIX_USE_CASES.md` - Bug fixes and patches
- API guides in `/docs` - Integration guides
- Inline code docstrings

---

## 🔒 Security Guidelines

**CRITICAL: Never commit credentials!**

### Before Committing
```bash
# Check for credentials
grep -r "ELAVMS[0-9]" .
grep -r "password" . | grep -v "your_password"
grep -r "[0-9]{7}" .  # Account IDs

# Verify .gitignore
cat .gitignore | grep credentials.json
```

### If You Accidentally Commit Credentials
1. **DO NOT** just delete and recommit
2. **Immediately** rotate the exposed credentials
3. **Contact maintainers** for help with git history cleanup
4. Use `git filter-branch` or BFG Repo-Cleaner to remove from history

---

## 🤝 Code of Conduct

### Our Standards
- Be respectful and professional
- Provide constructive feedback
- Accept constructive criticism gracefully
- Focus on what's best for the community

### Unacceptable Behavior
- Harassment or discriminatory language
- Trolling or insulting comments
- Publishing private information
- Unprofessional conduct

---

## 📞 Questions?

- **General questions:** Open a [Discussion](https://github.com/howardsinc3753/MSSP-Tools/discussions)
- **Bug reports:** [Issues](https://github.com/howardsinc3753/MSSP-Tools/issues)
- **Security issues:** Email maintainers directly (see README)

---

## 🎉 Recognition

Contributors will be recognized in:
- Release notes
- CONTRIBUTORS.md file
- Special thanks in README

---

**Thank you for contributing to the FortiFlex MSSP Toolkit!** 🚀

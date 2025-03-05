# 📏 Cursor Rules Repository

This directory serves as a centralized repository of coding rules, design patterns, and shared conventions for all projects. These rules are designed to be used with the Cursor IDE to ensure consistent code quality and maintainability across projects.

## 🎯 Purpose

- Provide standardized coding practices across all projects
- Maintain consistent design patterns and architectural approaches
- Ensure code quality through automated rule checking
- Reduce technical debt through enforced best practices

## 📂 Structure

### 1. 💡 Code Advice Rules (`001-code-advice-rules.mdc`)
Contains project-wide coding standards and best practices for AI code generation, including:
- Method deprecation verification requirements
- Confidence level requirements for code suggestions
- Simplicity-first approach to solutions
- Code example usage guidelines
- Standardized logging practices using loguru

### 2. 🧩 Design Patterns (`002-design-patterns.mdc`)
Documents common design patterns and their implementations, including:
- Async Processing Patterns
- Text Processing Patterns
- Caching Patterns
- Best practices for implementation

### 3. 📦 Package Usage (`003-package-usage.mdc`)
Guidelines for using common packages and utilities, including:
- Text processing with text_normalizer
- Caching and retries with caching_tenacity
- Best practices for package integration

### 4. 🔍 Testing Practices (`004-testing-practices.mdc`)
Guidelines for test organization and implementation, including:
- Progressive testing approach
- Test fixture usage
- Mock response handling

### 5. 📝 Structured Inputs (`005-structured-inputs.mdc`)
Guidelines for handling structured inputs and validation

### 6. 🛠️ UV Commands (`006-uv-commands.mdc`)
Rules for package management using UV, including:
- Package installation
- Dependency management
- Version control

### 7. ✅ Command Validation (`007-command-validation.mdc`)
Rules for validating commands before execution:
- Pre-command rule checking
- Command compliance validation
- Rule violation blocking

## 🛠️ Usage

1. **Project Integration**
   - Copy the `.cursor/rules` directory to your project root
   - Ensure Cursor IDE is configured to use these rules

2. **Rule Updates**
   - Rules should be versioned and dated
   - Changes should be documented in commit messages
   - Breaking changes should be clearly marked

3. **Contributing**
   - Follow the numbered file naming convention
   - Include clear descriptions and examples
   - Test rules before committing
   - Update relevant indexes when adding patterns

## 📝 File Naming Convention

- `001-*`: Core coding rules and standards
- `002-*`: Design patterns and architectural guidelines
- `003-*`: (Reserved for future use)

## 🔧 Maintenance

This repository is maintained as part of the common snippets project. To contribute:
1. Fork the repository
2. Make your changes
3. Submit a pull request with clear documentation

## 📦 Dependencies

- Cursor IDE
- Python 3.10+
- Standard development tools (linters, formatters)

## ✅ Best Practices

1. **Rule Application**
   - Apply rules consistently across projects
   - Document any project-specific exceptions
   - Keep rules updated with latest best practices

2. **Pattern Usage**
   - Reference patterns by their index number
   - Document pattern adaptations
   - Maintain backward compatibility

3. **Code Quality**
   - Follow confidence level guidelines
   - Use provided logging standards
   - Implement error handling as specified

## ❓ Support

For questions or issues:
1. Check existing documentation
2. Review pattern index
3. Submit an issue if needed

💡 Remember: These rules are living documents - they should evolve with your projects while maintaining consistency and quality.

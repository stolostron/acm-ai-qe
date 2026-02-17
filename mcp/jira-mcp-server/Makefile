# Jira MCP Server Makefile

SHELL := /bin/bash

.PHONY: help setup-prompts clean

# Default target
help:
	@echo "Available targets:"
	@echo "  setup-prompts  - Interactive setup of AI assistant prompt files"
	@echo "  clean         - Remove generated prompt files"
	@echo "  help          - Show this help message"

# Interactive setup for AI assistant prompts
setup-prompts:
	@echo "=== Jira MCP Server Prompt Setup ==="
	@echo ""
	@read -p "Enter your Jira project key (e.g., MYPROJ, DEV, ACME): " PROJECT_KEY; \
	if [ -z "$$PROJECT_KEY" ]; then \
		echo "Error: Project key cannot be empty"; \
		exit 1; \
	fi; \
	echo ""; \
	read -p "Enter your email address for default assignee (e.g., john.doe@company.com): " ASSIGNEE_EMAIL; \
	if [ -z "$$ASSIGNEE_EMAIL" ]; then \
		echo "Error: Assignee email cannot be empty"; \
		exit 1; \
	fi; \
	echo ""; \
	read -p "Enter your organization's security level (default: None): " SECURITY_LEVEL; \
	if [ -z "$$SECURITY_LEVEL" ]; then \
		SECURITY_LEVEL="None"; \
		echo "Using default security level: None"; \
	fi; \
	echo ""; \
	echo "Setting up prompt files with:"; \
	echo "  Project Key: $$PROJECT_KEY"; \
	echo "  Assignee Email: $$ASSIGNEE_EMAIL"; \
	echo "  Security Level: $$SECURITY_LEVEL"; \
	echo ""; \
	for FILE in CLAUDE.md GEMINI.md; do \
		echo "Creating $$FILE..."; \
		cp jira-assistant-prompt.md $$FILE; \
		sed -i.bak 's/"PROJ"/"'$$PROJECT_KEY'"/g' $$FILE; \
		sed -i.bak 's/PROJ-/'$$PROJECT_KEY'-/g' $$FILE; \
		sed -i.bak "s|SECURITY_PLACEHOLDER|$${SECURITY_LEVEL}|g" $$FILE; \
		sed -i.bak 's/- Assignee (`assignee`) - suggest "assign to me" if not specified/- Assignee (`assignee`) - suggest "assign to me" if not specified (default: "'$$ASSIGNEE_EMAIL'")/g' $$FILE; \
		rm $$FILE.bak; \
		echo "$$FILE created successfully"; \
	done
	echo ""; \
	echo "✅ Setup complete! Generated files:"; \
	echo "  - CLAUDE.md (for Claude Code)"; \
	echo "  - GEMINI.md (for Gemini CLI)"; \
	echo ""; \
	echo "Next steps:"; \
	echo "1. Configure your MCP client to use the Jira MCP server"; \
	echo "2. Set up your .env file with Jira credentials"; \
	echo "3. Start using your AI assistant with Jira integration!"

# Clean up generated files
clean:
	@echo "Removing generated prompt files..."
	@rm -f CLAUDE.md GEMINI.md
	@echo "✅ Cleanup complete!"
	
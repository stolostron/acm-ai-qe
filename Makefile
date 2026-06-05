PLUGIN_URL := git@github.com:stolostron/acm-ai-qe.git

.PHONY: install-claude install-dev uninstall lint validate test

install-claude: ## Install plugin from GitHub
	claude plugin marketplace add "$(PLUGIN_URL)"
	claude plugin install acm-ai-qe

install-dev: ## Install from local checkout (for development)
	claude plugin marketplace add "$$(pwd)"
	claude plugin install acm-ai-qe

uninstall: ## Remove plugin
	claude plugin uninstall acm-ai-qe
	claude plugin marketplace remove acm-ai-qe

lint: ## Validate skill frontmatter and check for hardcoded credentials
	@bash scripts/lint.sh

validate: ## Check skills/README.md matches what's on disk
	@bash scripts/validate-readmes.sh

test: ## Run all test suites
	cd apps/z-stream-analysis && python -m pytest tests/unit/ tests/regression/ -q
	cd apps/acm-hub-health && python -m pytest tests/regression/ -q
	cd apps/test-case-generator && python -m pytest tests/unit/ tests/integration/ -q
	@bash scripts/test-skill-paths.sh

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

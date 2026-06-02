.PHONY: lint format test coverage bench install-dev clean help build-release build-dev build-codex version verify-build

help:  ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install-dev:  ## 安装开发依赖
	pip install -e ".[dev]"

lint:  ## 运行 ruff 检查代码风格
	ruff check .

format:  ## 使用 ruff 格式化代码
	ruff format .
	ruff check --fix .

test:  ## 运行测试
	pytest

coverage:  ## 运行测试并生成覆盖率报告
	coverage run -m pytest
	coverage report
	coverage html
	@echo "HTML 覆盖率报告已生成到 htmlcov/ 目录"

bench:  ## 运行性能基准测试
	pytest tests/benchmark/ --benchmark-enable --benchmark-sort=name -v

clean:  ## 清理临时文件
	rm -rf __pycache__ app/__pycache__ tests/__pycache__
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	rm -rf build dist *.egg-info

build-release:  ## 打包正式发布版
	python scripts/build/build.py --variant release --clean

build-dev:  ## 打包开发调试版
	python scripts/build/build.py --variant dev --clean

build-codex:  ## 打包 Codex 账号切换器
	python scripts/build/build.py --variant codex --clean

version:  ## 显示当前版本
	python scripts/version_bump.py show

verify-build:  ## 验证构建配置（dry-run 模式，不实际打包）
	python scripts/build/build.py --variant release --dry-run
	@echo "构建配置验证通过"

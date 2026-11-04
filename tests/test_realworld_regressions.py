"""Cases found by scanning mature, human-written packages (requests, rich, openai, litellm...).

Each one was a false positive at first. They are kept here so the rules do not drift back.
"""

from conftest import ids

KEY = "sk-" + "Ab3dE6gH9jK2mN5pQ8sT1vW4yZ7cF0hJ3kL6"


def test_env_var_names_and_dotted_keys_are_not_secrets(scan):
    source = (
        'ENV_API_KEY = "ANTHROPIC_API_KEY"\n'
        'ENV_AUTH_TOKEN = "ANTHROPIC_AUTH_TOKEN"\n'
        'GRANT_TYPE_REFRESH_TOKEN = "refresh_token"\n'
        'LLM_TOKEN_COUNT_PROMPT = "llm.token_count.prompt"\n'
        'api_key_header = "X-Api-Key-Header-Value"\n'
        'AWS_SECRET_ENV = "AWS_SECRET_ACCESS_KEY_ID1"\n'
    )
    assert scan({"a.py": source}, rule_ids=("SEC-01",)) == []


def test_real_looking_credentials_are_still_found(scan):
    source = f'token = "q9X$kP2mZr7LwT4bNc"\nclient = Client(api_key="{KEY}")\nsecret = "9f86d081884c7d659a2feaa0c55ad015"\n'
    assert [f.line for f in scan({"a.py": source}, rule_ids=("SEC-01",))] == [1, 2, 3]


def test_documented_example_keys_are_ignored(scan):
    assert scan({"a.py": 'k = "AKIAIOSFODNN7EXAMPLE"\n'}, rule_ids=("SEC-01",)) == []


def test_private_key_header_needs_key_material(scan):
    header_only = 'PREFIX = "-----BEGIN RSA PRIVATE KEY-----"\nif PREFIX in text:\n    pass\n'
    placeholder = '{"placeholder": "-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----"}\n'
    body = "A" * 64
    real = f"-----BEGIN RSA PRIVATE KEY-----\n{body}\n-----END RSA PRIVATE KEY-----\n"
    assert scan({"a.py": header_only, "b.json": placeholder}, rule_ids=("SEC-01",)) == []
    assert ids(scan({"c.pem.py": real}, rule_ids=("SEC-01",))) == ["SEC-01"]


def test_ordinary_comments_that_mention_implementation_are_not_placeholders(scan):
    source = (
        "# provided a lot of what went into the implementation here in\n"
        "# if we have a known extends already we don't need that code here\n"
        "# Sneak in the reporting logic here\n"
    )
    assert scan({"a.py": source}, rule_ids=("INC-01",)) == []


def test_imperative_placeholders_are_still_found(scan):
    source = "# Implement rerank logic here based on the provider\n# Your client code here\n# add your code here\n"
    assert len(scan({"a.py": source}, rule_ids=("INC-01",))) == 3


def test_hook_methods_are_low_severity_and_documented_hooks_are_skipped(scan):
    source = (
        "class Base:\n"
        "    def close(self):\n        pass\n"
        "    def on_text(self, text):\n        '''Subclasses override this hook.'''\n"
        "def helper():\n    pass\n"
    )
    findings = scan({"a.py": source}, rule_ids=("INC-02",))
    by_name = {f.message.split("`")[1]: f for f in findings}
    assert set(by_name) == {"close", "helper"}
    assert by_name["close"].severity.label == "low" and by_name["close"].confidence < 0.5
    assert by_name["helper"].severity.label == "medium" and by_name["helper"].confidence > 0.8


def test_explained_swallow_and_narrow_catches_are_clean(scan):
    source = (
        "try:\n    cleanup()\nexcept Exception:  # best effort, the file may be gone\n    pass\n"
        "try:\n    cleanup()\nexcept Exception:\n    # nothing to do if the socket is closed\n    pass\n"
        "try:\n    value = d['k']\nexcept KeyError:\n    pass\n"
    )
    assert scan({"a.py": source}, rule_ids=("INC-04",)) == []


def test_endpoints_and_self_named_values_are_not_secrets(scan):
    source = (
        'TOKEN_ENDPOINT = "/v1/oauth/token"\n'
        'oauth_client_secret = "oauth-client-secret"\n'
        "'''Example api_key='d5349b7e1d1f4e0b8f6a2c9d3e5f7a1b'.'''\n"
    )
    assert scan({"a.py": source}, rule_ids=("SEC-01",)) == []


def test_notes_that_say_add_things_here_are_not_placeholders(scan):
    source = "# Add vertex_ai here once verified.\n# Add more providers here as needed\nx = 1  # Add any extra metadata here\n"
    assert scan({"a.py": source}, rule_ids=("INC-01",)) == []


def test_typed_ellipsis_stubs_are_low_severity(scan):
    source = "def get_origin(t: type) -> type | None: ...\n\ndef todo():\n    pass\n"
    by_name = {f.message.split("`")[1]: f for f in scan({"a.py": source}, rule_ids=("INC-02",))}
    assert by_name["get_origin"].severity.label == "low" and by_name["todo"].severity.label == "medium"


def test_import_names_that_differ_from_the_distribution_are_mapped(scan):
    source = "import pkg_resources\nimport zmq\nimport slugify\nimport grpc\n"
    found = scan({"a.py": source}, rule_ids=("HAL-01",), known_packages=frozenset(
        {"setuptools", "pyzmq", "python-slugify", "grpcio"}), network=True)
    assert found == []


def test_namespace_packages_and_new_stdlib_modules_are_not_missing_packages(scan):
    source = "import opentelemetry.trace\nimport opensearchpy\nimport tomllib\nimport annotationlib\n"
    found = scan({"a.py": source}, rule_ids=("HAL-01",), network=True,
                 known_packages=frozenset({"opentelemetry-api", "opensearch-py"}))
    assert found == []


def test_unknown_imports_in_optional_places_are_medium_not_high(scan):
    source = (
        "import ghostlib_top\n"
        "def lazy():\n    import ghostlib_lazy\n"
        "try:\n    import ghostlib_guarded\nexcept ImportError:\n    pass\n"
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import ghostlib_types\n"
    )
    found = {f.message.split("`")[1]: f for f in scan({"a.py": source}, rule_ids=("HAL-01",), network=True)}
    assert found["ghostlib_top"].severity.label == "high" and found["ghostlib_top"].confidence > 0.8
    for name in ("ghostlib_lazy", "ghostlib_guarded", "ghostlib_types"):
        assert found[name].severity.label == "medium" and found[name].confidence <= 0.5


# -- found by running slopguard on a real project (an agent with fixtures and a Postgres store) --


def test_a_fixture_importing_its_own_package_is_local(scan):
    files = {
        "pyproject.toml": '[project]\nname = "x"\nversion = "0"\ndependencies = ["requests"]\n',
        "fixtures/checkout_agent/agent.py": "from checkout_agent.tools import TOOLS\nfrom fixtures import helpers\n",
        "fixtures/checkout_agent/tools.py": "TOOLS = []\n",
        "fixtures/helpers.py": "X = 1\n",
    }
    found = scan(files, rule_ids=("HAL-01", "HAL-04"), network=True)
    assert [f for f in found if f.path == "fixtures/checkout_agent/agent.py"] == []


def test_a_manifest_next_to_the_code_counts(scan):
    files = {
        "requirements.txt": "requests\n",
        "fixtures/app/pyproject.toml": '[project]\nname = "app"\nversion = "0"\ndependencies = ["langgraph"]\n',
        "fixtures/app/agent.py": "import langgraph\n",
        "other.py": "import langgraph\n",
    }
    found = scan(files, rule_ids=("HAL-04",))
    assert [f.path for f in found] == ["other.py"]  # declared for fixtures/app, not for the rest


def test_psycopg_is_not_a_typo_of_psycopg2(scan):
    assert scan({"a.py": "import psycopg\nfrom pydantic_core import ErrorDetails\n"}, rule_ids=("HAL-03",)) == []


def test_a_credential_named_like_test_data_is_low_severity(scan):
    key = "sk-ant-" + "Ab3dE6gH9jK2mN5pQ8sT1vW4yZ7cF0hJ3kL6"
    source = f'FAKE_KEY = "{key}"\nTEST_API_KEY = "{key}"\nAPI_KEY = "{key}"\nlatest_token = "{key}"\n'
    found = {f.line: f for f in scan({"a.py": source}, rule_ids=("SEC-01",))}
    assert found[1].severity.label == "low" and found[2].severity.label == "low"
    assert "named like test data" in found[1].message
    assert found[3].severity.label == "critical"   # a normal name stays critical
    assert found[4].severity.label == "critical"   # "latest" must not read as "test"


def test_dev_and_environment_dependency_tables_count_as_declared(scan):
    pyproject = (
        '[project]\nname = "x"\nversion = "0"\ndependencies = ["requests"]\n'
        '[tool.uv]\ndev-dependencies = ["langgraph>=0.2"]\n'
        '[tool.pdm.dev-dependencies]\ntest = ["respx"]\n'
        '[tool.hatch.envs.default]\ndependencies = ["freezegun"]\nextra-dependencies = ["dirty-equals"]\n'
    )
    source = "import langgraph\nimport respx\nimport freezegun\nimport dirty_equals\nimport numpy\n"
    found = scan({"pyproject.toml": pyproject, "a.py": source}, rule_ids=("HAL-04",))
    assert [f.message.split("`")[1] for f in found] == ["numpy"]


def test_setup_cfg_and_pipfile_are_read(scan):
    setup_cfg = "[options]\ninstall_requires =\n    requests>=2\n    langgraph\n[options.extras_require]\ndev =\n    pytest\n"
    pipfile = '[packages]\nhttpx = "*"\n[dev-packages]\nrespx = "*"\n'
    source = "import requests\nimport langgraph\nimport pytest\nimport httpx\nimport respx\nimport numpy\n"
    found = scan({"setup.cfg": setup_cfg, "Pipfile": pipfile, "a.py": source}, rule_ids=("HAL-04",))
    assert [f.message.split("`")[1] for f in found] == ["numpy"]


def test_config_only_files_are_not_dependency_manifests(scan):
    files = {
        "pyproject.toml": "[tool.ruff]\nline-length = 100\n",
        "setup.cfg": "[flake8]\nmax-line-length = 100\n",
        "a.py": "import numpy\n",
    }
    assert scan(files, rule_ids=("HAL-04",)) == []  # nothing declares dependencies, so no opinion

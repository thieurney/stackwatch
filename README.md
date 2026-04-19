# stackwatch

> CLI tool to monitor and diff CloudFormation stack states across environments

---

## Installation

```bash
pip install stackwatch
```

Or install from source:

```bash
git clone https://github.com/yourname/stackwatch.git && cd stackwatch && pip install .
```

---

## Usage

Monitor a CloudFormation stack in real time:

```bash
stackwatch monitor --stack my-app-stack --region us-east-1
```

Diff stack states between two environments:

```bash
stackwatch diff --stack my-app-stack --env-a staging --env-b production
```

Watch for drift across all stacks in an account:

```bash
stackwatch scan --region us-east-1 --all
```

### Common Options

| Flag | Description |
|------|-------------|
| `--stack` | Stack name or ARN |
| `--region` | AWS region |
| `--profile` | AWS CLI profile to use |
| `--interval` | Polling interval in seconds (default: 10) |
| `--output` | Output format: `table`, `json`, `yaml` |

---

## Requirements

- Python 3.8+
- AWS credentials configured via `~/.aws/credentials` or environment variables

---

## License

This project is licensed under the [MIT License](LICENSE).
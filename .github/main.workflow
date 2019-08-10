workflow "tests - python37" {
  resolves = ["actions/setup-python@master"]
  on = "push"
}

action "Setup python" {
  uses = "actions/setup-python@master"
  runs = "pip install .[dev]"
}

action "actions/setup-python@master" {
  uses = "actions/setup-python@master"
  needs = ["Setup python"]
  runs = "pytest"
}

action "actions/setup-python@master-1" {
  uses = "actions/setup-python@master"
}

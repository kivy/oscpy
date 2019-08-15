workflow "tests - python37" {
  on = "push"
  resolves = ["install37"]
}

action "install37" {
  uses = "docker://python:3.7"
  runs = "sh .github/actions/scripts/setup.sh"
}

workflow "tests - python36" {
  on = "push"
  resolves = ["install36"]
}

action "install36" {
  uses = "docker://python:3.6"
  runs = "sh .github/actions/scripts/setup.sh"
}

workflow "tests - python35" {
  on = "push"
  resolves = ["install35"]
}

action "install35" {
  uses = "docker://python:3.5"
  runs = "sh .github/actions/scripts/setup.sh"
}

workflow "tests - python27" {
  on = "push"
  resolves = ["install27"]
}

action "install27" {
  uses = "docker://python:2.7"
  runs = "sh .github/actions/scripts/setup.sh"
}

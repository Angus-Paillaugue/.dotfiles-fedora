export BORG_REPO=server:/mnt/hdd2/pc-backup
export BORG_RSH="ssh"

borg create \
  --verbose \
  --stats \
  --progress \
  --show-rc \
  --exclude '**/node_modules' \
  --exclude '**/__pycache__' \
  --exclude '**/.git' \
  --exclude '**/.venv' \
  --exclude '**/*.iso' \
  ::fedora-{now:%Y-%m-%d_%H-%M} \
  $HOME/Documents \
  $HOME/Downloads \
  $HOME/Pictures \
  $HOME/Videos \
  $HOME/Music \
  $HOME/.gitconfig \
  $HOME/.zshrc \
  $HOME/.ssh \
  $HOME/.config

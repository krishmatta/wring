import click
import os
import yaml

@click.command()
def cli():
    config = load_config()
    click.echo(config["ring"]["email"])

def load_config():
    config_file_path = os.path.join(os.environ["HOME"], ".config/wring/config.yml")
    with open(config_file_path, "r") as f:
        return yaml.safe_load(f)

import click

@click.command()
@click.argument("argument")
def cli(argument):
    click.echo(argument)

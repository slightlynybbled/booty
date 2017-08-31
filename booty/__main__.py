import click


@click.command()
@click.option('--hexfile', '-h', help='The path to the hex file')
@click.option('--load', '-l', is_flag=True, help='Load the device with the hex file')
@click.option('--verify', '-v', is_flag=True, help='Verify device')
def main(hexfile, load, verify):
    print(hexfile)
    print(load)
    print(verify)

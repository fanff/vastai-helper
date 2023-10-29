import json
import os
import subprocess
import sys
from argparse import ArgumentParser
from pprint import pprint

import click
from vastai import vast


def list_instances(vastai_exe):
    res = subprocess.check_output(f"{vastai_exe} show instances --raw ", shell=True)
    json_res = json.loads(res)
    return json_res


def list_instance_matching_format(vastai_exe, query):
    print("used q", query)
    cmd = f"{vastai_exe} search offers '{query}' -o dph --raw "
    print("used command", cmd)
    res = subprocess.check_output(cmd, shell=True)
    insts = json.loads(res)
    return insts


def rent_machine(
    vastaiexe,
    machine_id,
    storage=30.28,
    image: str = "pytorch/pytorch",
    start_script: str = "",
):
    cmd = f"{vastaiexe} create instance {machine_id} --image {image} --disk {storage} --ssh --direct --onstart {start_script} --raw"

    print("used command", cmd)
    res = subprocess.check_output(cmd, shell=True)
    print("response ", res.decode("utf-8"))
    insts = json.loads(res)
    return insts


@click.group()
def cli():
    pass


@cli.command(
    help="""generate pretty ssh configuration to use with existing instances"""
)
@click.option("--vastaiexe", type=str, default="vastai", help="vastaiexe to use")
@click.option(
    "--vastaikey",
    type=str,
    default="~/.ssh/id_rsa_vast.ai",
    help="vastai sshkey to use",
)
def ssh_config(vastaiexe, vastaikey):
    ssh_template = """
host %s
    user root
    hostname %s
    port %s
    identityFile %s
"""

    json_res = list_instances(vastaiexe)
    for instance in json_res:
        instance_id = instance["id"]
        if "ports" in instance:
            ports = instance["ports"]

            public_ipaddr = instance["public_ipaddr"]
            portmap = ports["22/tcp"][0]["HostPort"]

            sshmp = ssh_template % (instance_id, public_ipaddr, portmap, vastaikey)

            print(sshmp)
        else:
            ports = instance["ssh_port"]
            public_ipaddr = instance["ssh_host"]
            sshmp = ssh_template % (
                str(instance_id) + "tun",
                public_ipaddr,
                ports,
                vastaikey,
            )

            print(sshmp)


@cli.command(help="""list instances""")
@click.option("--vastaiexe", type=str, default="vastai", help="vastaiexe to use")
def ls(vastaiexe):
    print(list_instances(vastaiexe))


@cli.command(
    help="""rent cheapest instance based on search\n Example:\n\n \
gpu_name==RTX_3090 num_gpus==1 rented=False verified=True
             """
)
@click.option(
    "--query",
    default="gpu_name==RTX_3090 num_gpus==1 rented=False verified=True",
    help="query to search for",
)
@click.option("--start_script", type=str, required=True, help="script to run on start")
@click.option("--storage", type=float, default=100, help="storage to allocate")
@click.option(
    "--image", type=str, default="pytorch/pytorch:latest", help="image to use"
)
@click.option("--vastaiexe", type=str, default="vastai", help="vastaiexe to use")
def rent(query, start_script, storage, image, vastaiexe):
    insts = list_instance_matching_format(
        vastaiexe, query + f" disk_space>{int(storage)*2}"
    )
    print("found %s instances" % len(insts))

    selected = insts[0]

    print(
        "selected instance:", selected["id"], selected["gpu_name"], selected["num_gpus"]
    )

    renting_response = rent_machine(
        vastaiexe,
        selected["id"],
        storage=storage,
        image=image,
        start_script=start_script,
    )
    print(renting_response)


@cli.command(
    help="""list available instances matching query\n Example:\n\n \
gpu_name==RTX_3090 num_gpus==1 rented=False verified=True disk_space>=100 
             """
)
@click.option("--vastaiexe", type=str, default="vastai", help="vastaiexe to use")
@click.option(
    "--query",
    default="gpu_name==RTX_3090 num_gpus==1 rented=False verified=True disk_space>=100",
    help="query to search for",
)
def query(vastaiexe, query):
    insts = list_instance_matching_format(vastaiexe, query)
    selection = ["id", "score", "num_gpus", "gpu_name", "disk_space", "dph_total"]
    print("\t".join(selection))
    for selected in insts:
        print("\t".join([str(selected[k]) for k in selection]))

    # for k in insts[0].keys():
    #     print(k)


if __name__ == "__main__":
    cli()

# Generate Topology Document

The generate_aap_cicd_topology_doc scaffolds the topology document skeleton. For more information on the various tologies refer to [the initiative](https://issues.redhat.com/browse/ANSTRAT-831).

## Usage

**1.** Provide the hanbook root path and the topology information in the [vars file](https://github.com/ansible/handbook/tree/main/tools/generate_aap_cicd_topology_doc/vars/main.yaml).

**2.** Run the [generate_markdown](https://github.com/ansible/handbook/tree/main/tools/generate_aap_cicd_topology_doc/generate_markdown.yaml) playbook as follows

```
ansible-playbook generate_markdown.yaml
```

This action creates a branch and adds a topology file, with each topology having its own separate file. The file contains a skeleton for the topology information, so add or edit the necessary details.

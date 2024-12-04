import re
from proxmoxer.core import ResourceException


def is_node_alive(connection, node):
    """
    Check if a node is reachable.  
    Useful for stopping automation tasks on nodes that are down.

    :param connection: An instance of the ProxmoxAPI.
    :param node: The name of the node the VM is running on.
    """
    try:
        # Get information about all nodes
        nodes = connection.nodes.get()

        # Check if the given node is in the list of nodes
        for n in nodes:
            if n["node"] == node:
                # Check if the node is reachable by making a simple API call
                try:
                    connection.nodes(node).status.get()
                    return True
                except ConnectionError:
                    # If the API call fails, the node is not reachable
                    return False

        # If node is not found, return False
        return False

    except Exception as e:
        print("Error:", e)
        return False
    

class ProxmoxVM:
    def __init__(self, proxmox_api, vm_id):
        """
        Initializes the ProxmoxVM instance with a node name, VM ID, and Proxmox API client instance.

        :param proxmox_api: object - An instance of the Proxmox API client.
        :param vm_id: int - The unique ID of the VM in the Proxmox cluster.
        """
        
        # 1. Initialize instance variables
        self.proxmox_api = proxmox_api
        self._vmid = vm_id
        self._node = None
        self._pool = None
        self._name = None
        self._tags = None
        self._cpu = None
        self._disk = None
        self._maxcpu = None
        self._maxdisk = None
        self._maxmem = None
        self._mem = None
        self._status = None
        self._storage = None
        self._uptime = None

        # 2. Retrieve VM information by iterating over VMs
        vm_found = False
        for each_vm in proxmox_api.cluster.resources.get(type='vm'):
            if each_vm.get('vmid') == self._vmid:
                self._node = each_vm.get('node')
                self._pool = each_vm.get('pool')
                self._name = each_vm.get('name')
                self._tags = each_vm.get('tags')
                self._cpu = each_vm.get('cpu')
                self._disk = each_vm.get('disk')
                self._maxcpu = each_vm.get('maxcpu')
                self._maxdisk = each_vm.get('maxdisk')
                self._maxmem = each_vm.get('maxmem')
                self._mem = each_vm.get('mem')
                self._status = each_vm.get('status')
                self._storage = each_vm.get('storage')
                self._uptime = each_vm.get('uptime')
                
                vm_found = True
                break
        
        # 3. Raise an exception if the VM was not found
        if not vm_found:
            raise ValueError(f"VM with ID {vm_id} not found in the Proxmox cluster.")
    
    
    def get_name(self):
        """Returns the name of the VM."""
        return self._name
    

    def set_name(self, new_name):
            """
            Rename a VM using its ID, ensuring the new name is a valid DNS name.

            :param new_name: The new name for the VM, which will be sanitized to ensure it's a valid DNS name.
            """
            
            def sanitize_dns_name(name):
                """
                Sanitize the input name to be a valid DNS name.

                :param name: The input name to be sanitized.
                :return: A sanitized version of the name, conforming to DNS naming conventions.
                """
                # Lowercase the name
                name = name.lower()
                # Replace invalid characters with hyphens
                name = re.sub(r"[^a-z0-9-]", "-", name)
                # Ensure it does not start or end with a hyphen
                name = name.strip("-")
                # Truncate to 253 characters
                name = name[:253]
                # Ensure each label is at most 63 characters
                name = ".".join(label[:63] for label in name.split("."))
                return name
            
            # Sanitize the new_name to be a valid DNS name
            sanitized_name = sanitize_dns_name(new_name)

            # Update the VM configuration with the new, sanitized name
            self.proxmox_api.nodes(self._node).qemu(self._vmid).config.put(name=sanitized_name)
    
    def get_node(self):
        """Returns the node name of the VM."""
        
        # To ensure that this returns a correct answer, use the API to confirm.
        vm_found = False
        for each_vm in self.proxmox_api.cluster.resources.get(type='vm'):
            if each_vm.get('vmid') == self._vmid:
                self._node = each_vm.get('node')
                vm_found = True
                break
        if not vm_found:
            return None
                
        return self._node


    def get_pool(self):
        """
        Returns the resource pool of the VM. Fetches from API if not already set.
        """
        if self._pool is None and self.get_node():
            try:
                vm_config = self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).config.get()
                self._pool = vm_config.get('pool')
            except Exception as e:
                print(f"Error fetching pool for VM {self._vmid}: {e}")
                return None
        return self._pool
    
    def set_pool(self, resource_pool_name):
        """
        Move the VM to a specified resource pool.
        
        :param resource_pool_name: str - The name of the resource pool to move the VM to.
        :return: bool - True if successful, False otherwise.
        """
        try:
            self.proxmox_api.pools(resource_pool_name).put(vms=self._vmid, **{'allow-move': 1})
            self._pool = resource_pool_name
            return True
        except Exception as e:
            print(f"Error setting pool for VM {self._vmid}: {e}")
            return False


    def start_vm(self):
        """
        Start the VM if it is not already running.
        """
        if self._status != 'running':
            try:
                self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).status.start.post()
                self._status = 'running'
                print(f"VM {self._vmid} started successfully.")
            except Exception as e:
                print(f"Error starting VM {self._vmid}: {e}")


    def stop_vm(self):
        """
        Stop the VM if it is currently running.
        """
        if self._status == 'running':
            try:
                self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).status.stop.post()
                self._status = 'stopped'
                print(f"VM {self._vmid} stopped successfully.")
            except Exception as e:
                print(f"Error stopping VM {self._vmid}: {e}")
                
    
    def reset_vm(self):
        """
        Reset the VM
        """
        if self._status == 'running':
            try:
                self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).status.reset.post()
                self._status = 'unknown'
                print(f"VM {self._vmid} reset successfully.")
            except Exception as e:
                print(f"Error reseting VM {self._vmid}: {e}")
                
    
    def start_vm(self):
        """
        Start the VM
        """
        if self._status != 'running':
            try:
                self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).status.start.post()
                self._status = 'unknown'
                print(f"VM {self._vmid} started successfully.")
            except Exception as e:
                print(f"Error reseting VM {self._vmid}: {e}")
                
                
    def stop_vm(self):
        """
        Stop the VM
        """
        if self._status != "stopped":
            try:
                self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).status.stop.post()
                self._status = 'stopped'
                print(f"VM {self._vmid} stopped successfully.")
            except Exception as e:
                print(f"Error reseting VM {self._vmid}: {e}")


    def get_status(self):
        """
        Get the current status of the VM (running, stopped, etc.)
        """
        return self._status


    def get_resource_usage(self):
        """
        Get current resource usage statistics for the VM.
        
        :return: dict - A dictionary with CPU, disk, memory usage and uptime.
        """
        return {
            "cpu": self._cpu,
            "disk": self._disk,
            "memory": self._mem,
            "uptime": self._uptime
        }


    def set_cpu(self, cores, sockets=1):
            """
            Sets the number of CPU sockets and cores for the VM.

            :param sockets: int - The number of CPU sockets.
            :param cores: int - The number of cores per socket.
            :return: bool - True if successful, False otherwise.
            """
            try:
                self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).config.put(sockets=sockets, cores=cores)
                self._maxcpu = sockets * cores
                print(f"CPU configuration set to {sockets} socket(s) with {cores} core(s) each.")
                return True
            except Exception as e:
                print(f"Error setting CPU for VM {self._vmid}: {e}")
                return False
            
    
    def set_memory(self, memory_gb):
        """
        Sets the amount of RAM for the VM in gigabytes.

        :param memory_gb: int - The amount of memory in GB.
        :return: bool - True if successful, False otherwise.
        """
        memory_mb = memory_gb * 1024  # Convert GB to MB as Proxmox API uses MB
        try:
            self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).config.put(memory=memory_mb)
            self._maxmem = memory_mb
            print(f"Memory configuration set to {memory_gb} GB.")
            return True
        except Exception as e:
            print(f"Error setting memory for VM {self._vmid}: {e}")
            return False
        
        
    def get_num_cpu(self):
        """
        Gets the total number of CPU cores for the VM (cores * sockets).

        :return: int - The total number of CPU cores.
        """
        try:
            # Fetch current configuration
            config = self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).config.get()
            sockets = config.get('sockets', 1)  # Default to 1 socket if not found
            cores = config.get('cores', 1)      # Default to 1 core if not found
            num_cpu = sockets * cores
            return int(num_cpu)
        except Exception as e:
            print(f"Error getting CPU info for VM {self._vmid}: {e}")
            return 0


    def get_gb_ram(self):
        """
        Gets the total amount of RAM for the VM in gigabytes.

        :return: int - The total amount of RAM in GB.
        """
        try:
            # Fetch current configuration
            config = self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).config.get()
            memory_mb = config.get('memory', 0)  # Fetch memory in MB
            memory_gb = int(memory_mb) // 1024        # Convert from MB to GB
            return int(memory_gb)
        except Exception as e:
            print(f"Error getting memory info for VM {self._vmid}: {e}")
            return 0
        

    def disconnect_network_adapter(self, i):
        """
        Disconnects a specified network adapter.

        :param net_id: str - The identifier of the network adapter to disconnect (e.g., 'net0', 'net1').
        :return: bool - True if successful, False otherwise.
        """
        net_adapter_config = {
            "link_down": 1,
            "model": "virtio"
        }
        adapter=f'net{i}'
        self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).config.put(**{adapter: ','.join([f"{k}={v}" for k, v in net_adapter_config.items()])})


    def connect_network_adapter(self, i):
        """
        Connects a network adapter to a specified bridge.

        :param net_id: str - The identifier of the network adapter to connect (e.g., 'net0', 'net1').
        :param bridge: str - The bridge to connect the network adapter to.
        :param model: str - The model of the network adapter (default is 'virtio').
        :return: bool - True if successful, False otherwise.
        """
        net_adapter_config = {
            "link_down": 0,
            "model": "virtio"
        }
        adapter=f'net{i}'
        self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).config.put(**{adapter: ','.join([f"{k}={v}" for k, v in net_adapter_config.items()])})

        
        
    def disconnect_net0_and_net1(self):
        """
        Disconnects all network adapters for the VM.
        
        :return: bool - True if all network adapters were successfully disconnected, False if any error occurred.
        """
        for i in range(0, 2):
            net_adapter_config = {
                "link_down": 1,
                "model": "virtio"
            }
            adapter=f'net{i}'
            self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).config.put(**{adapter: ','.join([f"{k}={v}" for k, v in net_adapter_config.items()])})
    
    
    def get_ha_group(self):
        ha_resources = self.proxmox_api.cluster.ha.resources.get()
        for resource in ha_resources:
            if resource['sid'] == f'vm:{self._vmid}':
                return resource.get('group', None)
        return None
    
    
    def get_ha_state(self):
        ha_resources = self.proxmox_api.cluster.ha.resources.get()
        for resource in ha_resources:
            if resource['sid'] == f'vm:{self._vmid}':
                return resource.get('state', None)
        return None
    
    
    def add_to_ha_group_started(self, group):
        # remove self from HA group if there's an error state
        ha_resources = self.proxmox_api.cluster.ha.resources.get()
        for resource in ha_resources:
            if resource['sid'] == f'vm:{self._vmid}':
                if resource['status'] == 'error':
                    self.remove_from_ha_group()
                    
        self.proxmox_api.cluster.ha.resources.create(sid=f'vm:{self._vmid}', group=group, state='started')
    
    
    def remove_from_ha_group(self):
        # Return if the HA group is already None
        if self.get_ha_group() == None:
            return

        # Disable HA management temporarily
        self.proxmox_api.cluster.ha.resources(f'vm:{self._vmid}').put(state='disabled')

        # Delete the VM from the HA group
        self.proxmox_api.cluster.ha.resources(f'vm:{self._vmid}').delete()
    
    
    def migrate_vm(self, node):
        if self.get_node() == node:
            return
        try:
            self.proxmox_api.nodes(self.get_node()).qemu(self._vmid).migrate.post(target=node, online=1)
        except ResourceException as e:
            print(e)
    
        
        
        
        

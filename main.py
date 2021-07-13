import requests
import json
import os 
import keyring
from netmiko import ConnectHandler
from csv import reader

#Function to add the device
def add_device(switch,headers,device_types_url,devices_url,empty_payload):
    
    #Connect to Switch and run commands
    c = ConnectHandler(**switch)
    c.enable() 
    interfaces = c.send_command('show ver' , use_textfsm=True)
    
    #Pull Information from Switch and store in variables
    name = interfaces[0]['hostname']
    serialnumber = interfaces[0]['serial']#Convert List to string for comparing
    physicaladdr = ''.join(serialnumber)
    devicetype= interfaces[0]['hardware']#Convert List to string for comparing
    type = ''.join(devicetype)

    #Looping through each device-type to check if there is anymatch
    response = requests.request("GET", device_types_url, headers=headers, data=empty_payload, verify=False)
    json_data = response.json()
    results = json_data['results']
    hardware = type
    for device in results: 
        model = device['model']
        if hardware ==  model:
            global type_id #Defining device_id as global variable so can be used in other functions.
            type_id = device['id']
   
    #Adding device with arguments
    payload={"name":name,"device_type": type_id ,"device_role": <device role id here> ,"site": <device site id here> , 'serial':  physicaladdr  }
    response = requests.request("POST", devices_url , headers=headers, json=payload, verify=False)
    json_data = response.json()
    global device_id #Defining device_id as global variable so can be used in other functions.  
    device_id  = json_data['id']

#Function to add the interface to device
def add_int(switch,headers,vlan_url,interface_url,empty_payload): 
    
    #Connect to Switch and run commands
    c = ConnectHandler(**switch)
    c.enable() 
    interfaces = c.send_command('show interfaces status' , use_textfsm=True)
    
    #Looping through each interface of the switch
    for interface in interfaces:
        name = interface['port'] 
        type = str('100base-tx')
        description = interface['name']
        intvlan = str(interface["vlan"])
        target_device = device_id

        #Adding Access Ports
        if intvlan != 'trunk':
             #Check and find vlan ID in netbox
            response = requests.request("GET",vlan_url, headers=headers, data=empty_payload, verify=False )
            json_data = response.json()
            results = json_data['results']
            newvlan = intvlan
            accessmode = "access"
            for device in results:
                vlan = device['vid']
                newvlan = intvlan
                id = device['id'] 
                if str(newvlan) ==  str(vlan):
                    payload={"device":target_device ,"name": name ,"type": type ,"description": description, "mode": accessmode , "untagged_vlan": id }
                    response = requests.request("POST", interface_url , headers=headers, json=payload, verify=False)
        #Adding Trunk Ports
        else: 
            mode = 'tagged'
            payload={"device":target_device ,"name": name ,"type": type ,"description": description, "mode": mode  }
            response = requests.request("POST", interface_url , headers=headers, json=payload, verify=False)

    #Adding Management vlan interface(Hardcoded)(Optional: You can delete this part if you don't want to add Vlan interface)    
    name = 'Vlan 200' 
    type = str('virtual')
    description = 'Management Vlan'
    payload={"device":target_device ,"name": name ,"type": type ,"description": description, "mode": mode  }
    response = requests.request("POST", interface_url, headers=headers, json=payload, verify=False)
    json_data = response.json()
    global interface_id #Defining interface_id as global variable so can be used in other functions.
    interface_id  = json_data['id']                       

#Function to add primary IP address to device (Optional: You can delete this part if you don't want to add Vlan interface)
def add_ip(headers,ipaddrs_url,devices_url,ip_add): 
    fulladdress = str(ip_add)+'/24'
    interface = interface_id
    payload={"address": fulladdress , "status":"active" , "assigned_object_id" : interface , "assigned_object_type" : "dcim.interface"}
    response = requests.request("POST",ipaddrs_url, headers=headers, json=payload, verify=False)
    json_data = response.json()
    ipadd_id  = json_data['id']

    #Make the IP address primary with PATCH request
    target_device_type_id = type_id
    url = str(devices_url)+str(device_id)+"/"
    payload={"device_type": target_device_type_id ,"device_role": 17 ,"site": 1 , "primary_ip4" : ipadd_id}
    response = requests.request("PATCH", url , headers=headers, json=payload, verify=False)
    print(ip_add + " succesfully added to NetBox.")

#Import list of IPs from Inventory file.
with open('inventory.csv', 'r') as read_obj:
    csv_reader = reader(read_obj) # pass the file object to reader() to get the reader object
    for row in csv_reader: # Iterate over each row in the csv using reader object
        ip_add = ''.join(row)
        try: 
            #Cisco Switch detials
            switch = {
                    'device_type': 'cisco_ios', 
                    'ip': ip_add, 
                    'username': "<cisco_switch_username>", 
                    'password': "<cisco_switch_password>", 
                    'port' : 22
                }
            #Netbox Details
            device_types_url = "<Your Netbox URL>/api/dcim/device-types/"
            devices_url = "<Your Netbox URL>/api/dcim/devices/"
            vlan_url = "<Your Netbox URL>/api/ipam/vlans/"
            interface_url = "<Your Netbox URL>/api/dcim/interfaces/"
            ipaddrs_url = "<Your Netbox URL>/api/ipam/ip-addresses/"
            headers = {
                    'Content-Type': 'application/json',
                    'Authorization': 'Token <Your Token Here>',
                    
                    }
            empty_payload = {} 
            add_device(switch,headers,device_types_url,devices_url,empty_payload)
            add_int(switch,headers,vlan_url,interface_url,empty_payload)
            add_ip(headers,ipaddrs_url,devices_url,ip_add)#(Optional: You can delete this part if you don't want to add Vlan interface)
        except Exception as e: 
                print(e)
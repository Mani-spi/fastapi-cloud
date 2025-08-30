import requests
from datetime import datetime

# url = "http://192.168.0.126:9000/submit/"
url = "http://157.173.222.91:8000/submit/"

# Running List
running_list_payload = {
    "functionCode": "Running List",
    "data": [
        {
            "batch_id": 110,
            "batch_name": "Batch 11",
            "machine_name": "DD Machine",
            "tank_id": 231,
            "tank_name": "Tank-ABCD",
            "request_from": "IR Machine",
            "request_date_time": datetime.now().isoformat(),
            "selected_flow_meter_id": 502,
            "selected_out_number": 555,
            "ChemRecords": [
                {
                    "index": 1,
                    "record_id": 104,
                    "group_no": 102,
                    "seq_no": 101,
                    "chem_id": 105,
                    "chem_name": "Sodium Hydroxide",
                    "chem_target_weight": 32,
                    "afterwash_target_weight": 40,
                    "chem_acutal_weight": 10,
                    "afterwash_actual_weight": 52,
                    "current_state": "Completed",
                    "current_report_status": "Reported",
                }
            ],
        }
    ]
}
resp = requests.post(url, json=running_list_payload)
print("Running List Response:", resp.status_code, resp.json())


# Waiting List
waiting_list_payload = {
    "functionCode": "Waiting List",
    "data": [
        {
            "BatchID": 201,
            "BatchName": "Waiting Batch",
            "FabricWt": "150kg",
            "MLR": "1:8",
            "MachineID": 44,
            "Chem_Records": [
                {
                    "BatchID": 201,
                    "RecordID": 301,
                    "GroupNo": 1,
                    "SeqNo": 1,
                    "ChemID": 999,
                    "ChemName": "NaCl",
                    "TankID": 12,
                    "Chem_TW_Kg": 10,
                    "Chem_AW_Kg": 12,
                    "AWash_TW_Kg": 5,
                    "AWash_AW_Kg": 6,
                    "Staus": "Queued",
                    "DispenseMachine": "DD",
                    "RequestType": "Auto",
                    "UserName": "Admin",
                    "Request_From": "Scheduler",
                    "Request_DateTime": datetime.now().isoformat(),
                    "Dispensed_DateTime": datetime.now().isoformat(),
                }
            ]
        }
    ]
}
resp = requests.post(url, json=waiting_list_payload)
print("Waiting List Response:", resp.status_code, resp.json())


# Flow details
flow_details_payload = {
    "functionCode": "Flow details",
    "data": {
        "FlowState": {
            "FlowMeterID": 1,
            "FlowSystemEnabled": True,
            "Out1_Enabled": True,
            "Out2_Enabled": False,
            "OperationMode": "Auto",
            "ProcessState": "Running",
            "ProcessState_SubState": 2,
            "IsAirOut1Busy": False,
            "IsAirOut2Busy": True,
            "FlowMeterReading": 1234,
            "NACKCode": "None"
        },
        "Flow_Request": {
            "batch_id": 109,
            "batch_name": "Batch 1",
            "machine_id": 10,
            "machine_name": "DD",
            "tank_id": 23,
            "tank_name": "Tank-ABC",
            "request_from": "IR Machine",
            "request_date_time": datetime.now().isoformat(),
            "selected_flow_meter_id": 502,
            "selected_out_number": 555,
            "ChemRecords": [
                {
                    "index": 2,
                    "record_id": 110,
                    "group_no": 103,
                    "seq_no": 102,
                    "chem_id": 106,
                    "chem_name": "Sulfuric Acid",
                    "chem_target_weight": 45,
                    "afterwash_target_weight": 50,
                    "chem_acutal_weight": 15,
                    "afterwash_actual_weight": 55,
                    "current_state": "In Progress",
                    "current_report_status": "Pending",
                    "dispensed_datetime": datetime.now().date().isoformat()
                }
            ]
        }
    }
}
resp = requests.post(url, json=flow_details_payload)
print("Flow Details Response:", resp.status_code, resp.json())


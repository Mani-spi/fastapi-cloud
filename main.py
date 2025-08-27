import asyncio
import json
from typing import Union, Optional, List
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from database import SessionLocal, engine
from fastapi import FastAPI, WebSocket, File, UploadFile, Form
from models import Base, Customer, MachineModel, SerialNumbers, CustomerUserModel, CustomerPrivilegeEnum, ManagementPrivilegeEnum, Management, ManagementUserModel, MachineDetails
from sqlalchemy.exc import IntegrityError
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
import io
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from typing import Union, List, Dict, Any
import uvicorn
import os
from fastapi.staticfiles import StaticFiles

app = FastAPI()
# Base.metadata.create_all(bind=engine)


# --- Initialize DB for MySQL ---
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# Allow all CORS for testing
# This allows any frontend (e.g., React, Vue, etc.) to make requests to this backend.
# In production, you should restrict origins to trusted domains.
# CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# data_updated_event: A flag that gets "set" when new data is submitted. WebSocket clients wait for this to push updates.
data_updated_event = asyncio.Event()

# Store latest data globally if needed
latest_data: Optional["SubmitRequest"] = None


# Dependency
# Every time a route needs a DB session, this function is called.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/management_privileges/", response_model=list[dict[str, str]])
async def get_management_privileges() -> list[dict[str, str]]:
    return [
        {"value": priv.name, "label": priv.value}
        for priv in ManagementPrivilegeEnum
    ]


@app.get("/privileges/", response_model=list[dict[str, str]])
async def get_privileges() -> list[dict[str, str]]:
    return [
        {"value": priv.name, "label": priv.value}
        for priv in CustomerPrivilegeEnum
    ]


def generate_rsa_key_pair() -> dict:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    return {
        "private_key": private_pem,
        "public_key": public_pem
    }


class MachineData(BaseModel):
    customerID: Union[str, int]
    machineID: Union[str, int]
    machineName: str
    batchID: Union[str, int]
    batchName: str


@app.get("/")
async def root():
    return {"message": "Connected to FastAPI backend!"}


class ChemRecord(BaseModel):
    index: int
    record_id: int
    group_no: int
    seq_no: int
    chem_id: int
    chem_name: str
    chem_target_weight: float
    afterwash_target_weight: float
    chem_acutal_weight: float
    afterwash_actual_weight: float
    current_state: str
    current_report_status: str
    dispensed_datetime: str


class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    gst: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    address: Optional[str] = None
    key_name: Optional[str] = None
    private_key: Optional[str] = None
    public_key: Optional[str] = None


class ManagementCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    gst: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    address: Optional[str] = None
    key_name: Optional[str] = None
    private_key: Optional[str] = None
    public_key: Optional[str] = None


class MachineCreate(BaseModel):
    machineName: str
    customer_id: int


class MachineModelBase(BaseModel):
    machineName: str
    model_number: str
    description: str
    default_warranty_months: int
    phase: str
    volts: str
    amps: str
    frequency: str
    sw_version: str
    pcb_version: str
    fw_version: str
    design_version: str
    make: int
    image: Optional[str]


class MachineModelCreate(MachineModelBase):
    pass


class MachineModelUpdate(MachineModelBase):
    pass


class MachineModelOut(MachineModelBase):
    id: int

    class Config:
        from_attributes = True


class SerialNumberBase(BaseModel):
    serial_number: str
    date_of_manufacturing: str
    additional_warranty_months: str
    warranty_end_date: str
    product_warranty: str
    sw_version: str
    pcb_version: str
    fw_version: str
    design_version: str
    model_number: int
    customer_id: int


class SerialNumberCreate(SerialNumberBase):
    pass


class SerialNumberUpdate(SerialNumberBase):
    pass


class SerialNumberOut(SerialNumberBase):
    id: int

    class Config:
        from_attributes = True


class MachineSerialNumberOut(BaseModel):
    id: int
    serial_number: str

    class Config:
        from_attributes = True


class MachineOut(BaseModel):
    id: int
    machineName: str
    model_number: str
    description: str
    default_warranty_months: int
    phase: str
    volts: str
    amps: str
    frequency: str
    sw_version: str
    pcb_version: str
    fw_version: str
    design_version: str
    make: int
    image: Optional[str]
    serial_numbers: List[MachineSerialNumberOut] = []

    class Config:
        from_attributes = True


class CustomerUserCreate(BaseModel):
    name: str
    username: str
    password: str
    designation: str
    privilege: str
    customer_id: int


class ManagementUserCreate(BaseModel):
    name: str
    username: str
    password: str
    designation: str
    privilege: str
    management_id: int


router = APIRouter(prefix="/machines", tags=["Machines"])


@app.post("/create_machines", response_model=MachineModelOut)
def create_machine(machine: MachineModelCreate, db: Session = Depends(get_db)):
    db_machine = MachineModel(**machine.dict())
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)
    return db_machine


def compress_image(
        upload_file: UploadFile,
        model_number: str,
        output_dir: str = "static/images",
        max_size=(800, 800),
        quality=75
) -> str:
    image_data = upload_file.file.read()
    image = Image.open(io.BytesIO(image_data))

    # Convert to RGB (JPEG doesn't support alpha channels)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Resize
    image.thumbnail(max_size)

    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Sanitize and build filename
    model_base = os.path.splitext(model_number)[0]  # Remove .png or .jpg etc.
    ext = ".jpg"  # Force JPEG
    filename = f"{model_base}{ext}"
    output_path = os.path.join(output_dir, filename)

    # Save as compressed JPEG
    image.save(output_path, format="JPEG", optimize=True, quality=quality)

    return f"/{output_path.replace(os.sep, '/')}"  # Return as web path


@app.post("/upload_machine_model/")
async def upload_machine_model(
        machineName: str = Form(...),
        model_number: str = Form(...),
        description: str = Form(...),
        default_warranty_months: int = Form(...),
        phase: str = Form(...),
        volts: str = Form(...),
        amps: str = Form(...),
        frequency: str = Form(...),
        sw_version: str = Form(...),
        pcb_version: str = Form(...),
        fw_version: str = Form(...),
        design_version: str = Form(...),
        make: int = Form(...),
        image: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    import os
    os.makedirs("static/images", exist_ok=True)
    image_path = None
    # if image:
    #     filename = f"{model_number}_{image.filename}"
    #     filepath = f"static/images/{filename}"
    #     with open(filepath, "wb") as f:
    #         f.write(await image.read())
    #     image_path = f"/static/images/{filename}"

    if image:
        filename = f"{model_number}_{image.filename}"
        filepath = f"{filename}"
        compress_image(image, filepath)  # Compress and save
        image_path = f"/static/images/{filename}"

    new_machine = MachineModel(
        machineName=machineName,
        model_number=model_number,
        description=description,
        default_warranty_months=default_warranty_months,
        phase=phase,
        volts=volts,
        amps=amps,
        frequency=frequency,
        sw_version=sw_version,
        pcb_version=pcb_version,
        fw_version=fw_version,
        design_version=design_version,
        make=make,
        image=image_path
    )
    db.add(new_machine)
    db.commit()
    db.refresh(new_machine)
    return new_machine


@app.put("/update_machine_model/{machine_id}/", response_model=MachineModelOut)
async def update_machine_model(
        machine_id: int,
        machineName: str = Form(...),
        model_number: str = Form(...),
        description: str = Form(...),
        default_warranty_months: int = Form(...),
        phase: str = Form(...),
        volts: str = Form(...),
        amps: str = Form(...),
        frequency: str = Form(...),
        sw_version: str = Form(...),
        pcb_version: str = Form(...),
        fw_version: str = Form(...),
        design_version: str = Form(...),
        make: int = Form(...),
        image: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    db_machine = db.query(MachineModel).filter(MachineModel.id == machine_id).first()
    if not db_machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    if image:
        if db_machine.image:
            # Convert image path to .jpg (regardless of what was stored)
            old_path = db_machine.image.lstrip("/")
            base, _ = os.path.splitext(old_path)
            corrected_path = base + ".jpg"

            old_full_path = os.path.join(os.getcwd(), corrected_path)

            if os.path.isfile(old_full_path):
                os.remove(old_full_path)

        # 2. Save new image
        os.makedirs("static/images", exist_ok=True)
        filename = f"{model_number}_{image.filename}"
        filepath = f"{filename}"
        # with open(filepath, "wb") as f:
        #     f.write(await image.read())
        # db_machine.image = f"/static/images/{filename}"

        compress_image(image, filepath)  # Compress and save
        image_path = f"/static/images/{filename}"
        db_machine.image = f"{image_path}"

    db_machine.machineName = machineName
    db_machine.model_number = model_number
    db_machine.description = description
    db_machine.default_warranty_months = default_warranty_months
    db_machine.phase = phase
    db_machine.volts = volts
    db_machine.amps = amps
    db_machine.frequency = frequency
    db_machine.sw_version = sw_version
    db_machine.pcb_version = pcb_version
    db_machine.fw_version = fw_version
    db_machine.design_version = design_version
    db_machine.make = make

    db.commit()
    db.refresh(db_machine)
    return db_machine


@app.get("/machines/")
def list_machines(db: Session = Depends(get_db)):
    return db.query(MachineModel).all()


@app.put("/machines/{machine_id}/", response_model=MachineModelOut)
def update_machine(machine_id: int, machine: MachineModelUpdate, db: Session = Depends(get_db)):
    db_machine = db.query(MachineModel).filter(MachineModel.id == machine_id).first()
    if not db_machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    for key, value in machine.dict().items():
        setattr(db_machine, key, value)
    db.commit()
    db.refresh(db_machine)
    return db_machine


@app.delete("/machines/{machine_id}/", status_code=204)
def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    db_machine = db.query(MachineModel).filter(MachineModel.id == machine_id).first()
    if not db_machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    # 🧹 Delete associated image file if it exists
    if db_machine.image:
        image_path = os.path.splitext(db_machine.image.lstrip("/"))[0] + ".jpg"
        full_path = os.path.join(os.getcwd(), image_path)
        if os.path.isfile(full_path):
            os.remove(full_path)

    db.delete(db_machine)
    db.commit()
    return


@app.get("/serial_exists/{serial_number}", response_model=bool)
def check_serial_exists(serial_number: str, db: Session = Depends(get_db)):
    return db.query(SerialNumbers).filter(SerialNumbers.serial_number == serial_number).first() is not None


@app.post("/create_serial", response_model=SerialNumberOut)
def create_serial(serial: SerialNumberCreate, db: Session = Depends(get_db)):
    db_serial = SerialNumbers(**serial.dict())
    db.add(db_serial)
    db.commit()
    db.refresh(db_serial)
    data_updated_event.set()
    return db_serial


@app.get("/serial", response_model=list[SerialNumberOut])
def get_all_serials(db: Session = Depends(get_db)):
    return db.query(SerialNumbers).all()


@app.put("/serial/{serial_id}", response_model=SerialNumberOut)
def update_serial(serial_id: int, serial: SerialNumberUpdate, db: Session = Depends(get_db)):
    db_serial = db.query(SerialNumbers).filter(SerialNumbers.id == serial_id).first()
    if not db_serial:
        raise HTTPException(status_code=404, detail="Serial number not found")
    for key, value in serial.dict().items():
        setattr(db_serial, key, value)
    db.commit()
    db.refresh(db_serial)
    data_updated_event.set()
    return db_serial


@app.delete("/serial/{serial_id}", status_code=204)
def delete_serial(serial_id: int, db: Session = Depends(get_db)):
    db_serial = db.query(SerialNumbers).filter(SerialNumbers.id == serial_id).first()
    if not db_serial:
        raise HTTPException(status_code=404, detail="Serial number not found")
    db.delete(db_serial)
    db.commit()
    data_updated_event.set()
    return {"message": "Serial number deleted"}


@app.post("/customers/", status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    key_pair = generate_rsa_key_pair()
    customer = Customer(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        gst=payload.gst,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        key_name=payload.key_name,
        private_key=key_pair["private_key"],
        public_key=key_pair["public_key"],
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "gst": customer.gst,
        "latitude": customer.latitude,
        "longitude": customer.longitude,
        "address": customer.address,
        "private_key": customer.private_key,
        "public_key": customer.public_key,
        "key_name": customer.key_name
    }


@app.post("/management/", status_code=201)
def create_management(payload: ManagementCreate, db: Session = Depends(get_db)):
    key_pair = generate_rsa_key_pair()
    management = Management(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        gst=payload.gst,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        key_name=payload.key_name,
        private_key=key_pair["private_key"],
        public_key=key_pair["public_key"],
    )
    db.add(management)
    db.commit()
    db.refresh(management)
    return {
        "id": management.id,
        "name": management.name,
        "phone": management.phone,
        "email": management.email,
        "gst": management.gst,
        "latitude": management.latitude,
        "longitude": management.longitude,
        "address": management.address,
        "private_key": management.private_key,
        "public_key": management.public_key,
        "key_name": management.key_name
    }


@app.post("/customer_users/", status_code=201)
def create_customer_user(payload: CustomerUserCreate, db: Session = Depends(get_db)):
    customer_user = CustomerUserModel(name=payload.name, username=payload.username, password=payload.password,
                                      designation=payload.designation, privilege=payload.privilege, customer_id=payload.customer_id)
    try:
        db.add(customer_user)
        db.commit()
        db.refresh(customer_user)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig))
    # wake up any WebSocket dashboards if you need
    return {"id": customer_user.id, "name": customer_user.name, "username": customer_user.username, "password": customer_user.password,
            "designation": customer_user.designation, "privilege": customer_user.privilege, "customer_id": customer_user.customer_id}


@app.post("/create_management_users/", status_code=201)
def create_management_user(payload: ManagementUserCreate, db: Session = Depends(get_db)):
    management_user = ManagementUserModel(name=payload.name, username=payload.username, password=payload.password,
                                          designation=payload.designation, privilege=payload.privilege, management_id=payload.management_id)
    try:
        db.add(management_user)
        db.commit()
        db.refresh(management_user)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig))
    return {"id": management_user.id, "name": management_user.name, "username": management_user.username, "password": management_user.password,
            "designation": management_user.designation, "privilege": management_user.privilege, "management_id": management_user.management_id}


@app.post("/machines/", status_code=201)
def create_machine(payload: MachineCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    machine = MachineModel(
        machineName=payload.machineName,
        customer_id=payload.customer_id
    )
    db.add(machine)
    db.commit()
    db.refresh(machine)
    data_updated_event.set()
    return {
        "id": machine.id,
        "machineName": machine.machineName,
        "customer_id": machine.customer_id
    }


@app.put("/customers/{customer_id}/")
def update_customer(customer_id: int, payload: CustomerCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.name = payload.name
    customer.phone = payload.phone
    customer.email = payload.email
    customer.gst = payload.gst
    customer.latitude = payload.latitude
    customer.longitude = payload.longitude
    customer.address = payload.address
    customer.key_name = payload.key_name
    customer.private_key = payload.private_key
    customer.public_key = payload.public_key
    db.commit()
    db.refresh(customer)
    return {"id": customer.id, "name": customer.name, "phone": customer.phone, "email": customer.email,
            "gst": customer.gst, "latitude": customer.latitude, "longitude": customer.longitude,
            "address": customer.address, "key_name": customer.key_name, "private_key": customer.private_key, "public_key": customer.public_key}


@app.put("/management/{management_id}/")
def update_management(management_id: int, payload: ManagementCreate, db: Session = Depends(get_db)):
    management = db.query(Management).filter(Management.id == management_id).first()
    if not management:
        raise HTTPException(status_code=404, detail="Management not found")
    management.name = payload.name
    management.phone = payload.phone
    management.email = payload.email
    management.gst = payload.gst
    management.latitude = payload.latitude
    management.longitude = payload.longitude
    management.address = payload.address
    management.key_name = payload.key_name
    management.private_key = payload.private_key
    management.public_key = payload.public_key
    db.commit()
    db.refresh(management)
    return {"id": management.id, "name": management.name, "phone": management.phone, "email": management.email,
            "gst": management.gst, "latitude": management.latitude, "longitude": management.longitude,
            "address": management.address, "key_name": management.key_name, "private_key": management.private_key, "public_key": management.public_key}


@app.put("/customer_users/{user_id}/")
def update_customer_users(user_id: int, payload: CustomerUserCreate, db: Session = Depends(get_db)):
    customer_users = db.query(CustomerUserModel).filter(CustomerUserModel.id == user_id).first()
    if not customer_users:
        raise HTTPException(status_code=404, detail="User's not found")
    customer_users.name = payload.name
    customer_users.username = payload.username
    customer_users.password = payload.password
    customer_users.designation = payload.designation
    customer_users.privilege = payload.privilege
    customer_users.customer_id = payload.customer_id
    db.commit()
    db.refresh(customer_users)
    return {"id": customer_users.id, "name": customer_users.name, "username": customer_users.username, "password": customer_users.password,
            "designation": customer_users.designation, "privilege": customer_users.privilege, "customer_id": customer_users.customer_id}


@app.put("/management_users/{user_id}/")
def update_management_users(user_id: int, payload: ManagementUserCreate, db: Session = Depends(get_db)):
    management_users = db.query(ManagementUserModel).filter(ManagementUserModel.id == user_id).first()
    if not management_users:
        raise HTTPException(status_code=404, detail="User's not found")
    management_users.name = payload.name
    management_users.username = payload.username
    management_users.password = payload.password
    management_users.designation = payload.designation
    management_users.privilege = payload.privilege
    management_users.management_id = payload.management_id
    db.commit()
    db.refresh(management_users)
    return {"id": management_users.id, "name": management_users.name, "username": management_users.username, "password": management_users.password,
            "designation": management_users.designation, "privilege": management_users.privilege, "management_id": management_users.management_id}


@app.delete("/delete_customers/{customer_id}", status_code=204)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(customer)
    db.commit()
    return


@app.delete("/delete_management/{management_id}", status_code=204)
def delete_management(management_id: int, db: Session = Depends(get_db)):
    management = db.query(Management).filter(Management.id == management_id).first()
    if not management:
        raise HTTPException(status_code=404, detail="Management not found")
    db.delete(management)
    db.commit()
    return


@app.delete("/customer_users/{user_id}", status_code=204)
def delete_customer_users(user_id: int, db: Session = Depends(get_db)):
    customer_users = db.query(CustomerUserModel).filter(CustomerUserModel.id == user_id).first()
    if not customer_users:
        raise HTTPException(status_code=404, detail="User's not found")
    db.delete(customer_users)
    db.commit()
    return


@app.delete("/management_users/{user_id}", status_code=204)
def delete_management_users(user_id: int, db: Session = Depends(get_db)):
    management_users = db.query(ManagementUserModel).filter(ManagementUserModel.id == user_id).first()
    if not management_users:
        raise HTTPException(status_code=404, detail="User's not found")
    db.delete(management_users)
    db.commit()
    return


@app.websocket("/ws/machines/")
async def websocket_machines(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await data_updated_event.wait()  # wait until something updates
            await websocket.send_json({"event": "machine_data_updated"})
            data_updated_event.clear()  # reset the flag
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.get("/customers/")
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()


@app.get("/management/")
def list_management(db: Session = Depends(get_db)):
    return db.query(Management).all()


@app.get("/customer_users/")
def list_customer_users(customer_id: int = None, db: Session = Depends(get_db)):
    query = db.query(CustomerUserModel)
    if customer_id is not None:
        query = query.filter(CustomerUserModel.customer_id == customer_id)
    return query.all()


@app.get("/management_users/")
def list_management_users(management_id: int = None, db: Session = Depends(get_db)):
    query = db.query(ManagementUserModel)
    if management_id is not None:
        query = query.filter(ManagementUserModel.management_id == management_id)
    return query.all()


@app.get("/get_machines/", response_model=List[MachineOut])
def list_machines(
        customer_id: int | None = None,
        db: Session = Depends(get_db)
):
    query = db.query(MachineModel)

    if customer_id is not None:
        query = (
            db.query(MachineModel)
            .join(MachineModel.serial_numbers)
            .filter(SerialNumbers.customer_id == customer_id)
            .options(joinedload(MachineModel.serial_numbers))
            .distinct()
        )
    return query.all()


class EncryptedDataOnly(BaseModel):
    encrypted_key: str
    iv: str
    encrypted_data: str


def normalize_pem(pem_str: str) -> str:
    return pem_str.replace("\\n", "\n").replace("\r\n", "\n").strip()


def load_public_key_bytes(pem_str: str) -> bytes:
    return serialization.load_pem_public_key(
        normalize_pem(pem_str).encode(),
        backend=default_backend()
    ).public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )


# store data per functionCode
dashboard_store = {
    "Running List": [],
    "Waiting List": [],
    "Flow details": {}
}


class SubmitPayload(BaseModel):
    functionCode: str
    data: Union[Dict[str, Any], List[Dict[str, Any]]]


@app.post("/submit/")
async def submit_data(payload: SubmitPayload):
    global dashboard_store

    # ✅ Print incoming data in server logs
    print("\n=== New Data Received ===")
    print("FunctionCode:", payload.functionCode)
    print("Data:", payload.data)
    print("=========================\n")

    # store into correct section
    dashboard_store[payload.functionCode] = payload.data

    # trigger websocket update
    data_updated_event.set()
    data_updated_event.clear()

    return {"status": "success", "functionCode": payload.functionCode}


@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Send initial snapshot
    await websocket.send_text(json.dumps(dashboard_store))

    while True:
        await data_updated_event.wait()
        data_updated_event.clear()
        await websocket.send_text(json.dumps(dashboard_store))


@app.get("/get_dashboard/")
async def get_dashboard():
    return dashboard_store


@app.get("/response/")
async def get_latest_response():
    if latest_data is None:
        return {"message": "No data received yet"}
    return {
        "message": "Latest data received",
        "data": latest_data.dict()
    }


if __name__ == "__main__":

    # Ensure static folder exists
    os.makedirs("static/images", exist_ok=True)

    # Mount static folder to serve images
    app.mount("/static", StaticFiles(directory="static"), name="static")

    uvicorn.run(app, host="0.0.0.0", port=9000)


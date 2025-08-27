from enum import Enum
from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON
from database import Base
from sqlalchemy.orm import relationship


class ManagementPrivilegeEnum(str, Enum):
    Admin = "Admin"
    Top_Manager = "Top Manager"
    Manager_Production = "Manager-Production"
    Manager_Service = "Manager-Service"


class CustomerPrivilegeEnum(str, Enum):
    Admin = "Admin"
    Manager = "Manager"
    Engineer = "Engineer"
    Lab_Incharge = "Lab Incharge"


class DataEntry(Base):
    __tablename__ = "data_entries"

    id = Column(Integer, primary_key=True, index=True)
    functionCode = Column(String(500))
    machine_name = Column(String(500))
    batch_id = Column(String(500))
    batch_name = Column(String(500))

    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    customer = relationship("Customer", back_populates="data_entry")

    machine_id = Column(Integer, ForeignKey("machine_model.id", ondelete="CASCADE"), nullable=False)
    machine = relationship("MachineModel", back_populates="data_entry_machines")


class MachineDetails(Base):
    __tablename__ = "machine_details"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer)
    batch_name = Column(String(500))
    machine_name = Column(String(500))
    tank_id = Column(Integer)
    tank_name = Column(String(500))
    request_from = Column(String(500))
    request_date_time = Column(String(500))
    selected_flow_meter_id = Column(Integer)
    selected_out_number = Column(Integer)
    ChemRecords = Column(JSON)  # Storing the list of ChemRecords

    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    Client = relationship("Customer", back_populates="client_data")


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    phone = Column(String(20))
    email = Column(String(255))
    gst = Column(String(50))
    latitude = Column(String(500))
    longitude = Column(String(500))
    address = Column(Text)

    private_key = Column(Text)
    public_key = Column(Text)
    key_name = Column(String(500))

    # machines = relationship("MachineModel", back_populates="customer", cascade="all, delete")
    customer_users = relationship("CustomerUserModel", back_populates="customer", cascade="all, delete")
    customer_serial = relationship("SerialNumbers", back_populates="customer_serial", cascade="all, delete")
    data_entry = relationship("DataEntry", back_populates="customer", cascade="all, delete")
    client_data = relationship("MachineDetails", back_populates="Client", cascade="all, delete")


class Management(Base):
    __tablename__ = "management"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)

    phone = Column(String(20))
    email = Column(String(100))
    gst = Column(String(500))
    latitude = Column(String(500))
    longitude = Column(String(500))
    address = Column(Text)

    private_key = Column(Text)
    public_key = Column(Text)
    key_name = Column(String(500))

    machines = relationship("MachineModel", back_populates="machineMake", cascade="all, delete")
    management_users = relationship("ManagementUserModel", back_populates="management", cascade="all, delete")
    # data_entry = relationship("DataEntry", back_populates="customer", cascade="all, delete")


class ManagementUserModel(Base):
    __tablename__ = "management_user_model"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    username = Column(String(500), unique=True, nullable=False)
    password = Column(String(500), unique=True, nullable=False)
    designation = Column(String(800), nullable=False)
    privilege = Column(String(500), nullable=False)

    management_id = Column(Integer, ForeignKey("management.id", ondelete="CASCADE"), nullable=False)
    management = relationship("Management", back_populates="management_users")


class CustomerUserModel(Base):
    __tablename__ = "customer_user_model"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    username = Column(String(500), unique=True, nullable=False)
    password = Column(String(500), unique=True, nullable=False)
    designation = Column(String(800), nullable=False)
    privilege = Column(String(500), nullable=False)

    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    customer = relationship("Customer", back_populates="customer_users")


class MachineModel(Base):
    __tablename__ = "machine_model"
    id = Column(Integer, primary_key=True, index=True)
    machineName = Column(String(500), nullable=False)
    model_number = Column(String(500), unique=True, nullable=False)
    description = Column(String(800), nullable=False)
    default_warranty_months = Column(Integer, nullable=False)
    phase = Column(String(20), nullable=False)
    volts = Column(String(500), nullable=False)
    amps = Column(String(500), nullable=False)
    frequency = Column(String(500), nullable=False)
    image = Column(String(800), nullable=False)
    sw_version = Column(String(500), nullable=False)
    pcb_version = Column(String(500), nullable=False)
    fw_version = Column(String(500), nullable=False)
    design_version = Column(String(500), nullable=False)

    make = Column(Integer, ForeignKey("management.id", ondelete="CASCADE"), nullable=False)
    machineMake = relationship("Management", back_populates="machines")

    data_entry_machines = relationship("DataEntry", back_populates="machine", cascade="all, delete")

    # Optional: Add reverse relation for serial numbers
    serial_numbers = relationship("SerialNumbers", back_populates="machine_model", cascade="all, delete-orphan")


class SerialNumbers(Base):
    __tablename__ = "serial_numbers"
    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String(500), unique=True, nullable=False)
    date_of_manufacturing = Column(String(500), nullable=False)
    additional_warranty_months = Column(String(500), nullable=False)
    warranty_end_date = Column(String(500), nullable=False)
    product_warranty = Column(String(500), nullable=False)
    sw_version = Column(String(500), nullable=False)
    pcb_version = Column(String(500), nullable=False)
    fw_version = Column(String(500), nullable=False)
    design_version = Column(String(500), nullable=False)

    model_number = Column(Integer, ForeignKey("machine_model.id", ondelete="CASCADE"), nullable=False)
    machine_model = relationship("MachineModel", back_populates="serial_numbers")

    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    customer_serial = relationship("Customer", back_populates="customer_serial")

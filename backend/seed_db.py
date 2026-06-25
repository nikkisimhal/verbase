

import random
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy import (
    Column, Date, DateTime, Float, ForeignKey, Integer, String, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker

fake = Faker()
Base = declarative_base()


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    city = Column(String)
    signup_date = Column(Date)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String)
    price = Column(Float, nullable=False)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    order_date = Column(DateTime)
    status = Column(String)


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)


CATEGORIES = ["Electronics", "Home & Kitchen", "Books", "Fashion", "Sports", "Beauty"]
STATUSES = ["delivered", "shipped", "pending", "cancelled"]


def build_demo_db(db_path: str = "verbase_demo.db", n_customers=120, n_products=40, n_orders=400):
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    customers = [
        Customer(
            name=fake.name(),
            email=fake.email(),
            city=fake.city(),
            signup_date=fake.date_between(start_date="-2y", end_date="-1M"),
        )
        for _ in range(n_customers)
    ]
    session.add_all(customers)
    session.commit()

    products = [
        Product(
            name=fake.word().capitalize() + " " + random.choice(["Pro", "Max", "Lite", "Plus", ""]),
            category=random.choice(CATEGORIES),
            price=round(random.uniform(199, 24999), 2),
        )
        for _ in range(n_products)
    ]
    session.add_all(products)
    session.commit()

    orders = []
    for _ in range(n_orders):
        cust = random.choice(customers)
        order_date = datetime.now() - timedelta(days=random.randint(0, 365))
        orders.append(
            Order(customer_id=cust.id, order_date=order_date, status=random.choice(STATUSES))
        )
    session.add_all(orders)
    session.commit()

    items = []
    for order in orders:
        for _ in range(random.randint(1, 4)):
            items.append(
                OrderItem(
                    order_id=order.id,
                    product_id=random.choice(products).id,
                    quantity=random.randint(1, 5),
                )
            )
    session.add_all(items)
    session.commit()
    session.close()
    print(f"Seeded demo database at {db_path}: "
          f"{n_customers} customers, {n_products} products, {n_orders} orders, {len(items)} order items.")


if __name__ == "__main__":
    build_demo_db()

---
id: shipping-orders
title: Shipping and Order Lookup
last_updated: 2026-07-08
---

# Shipping and Order Lookup

## Order statuses

Online orders move through these statuses in the order system (OMS):

- processing: payment captured, not yet handed to the carrier. Address changes and
  cancellations are possible only in this status.
- shipped: with the carrier, tracking number attached. No address changes; do not
  promise redirects, carriers refuse them for retail parcels.
- delivered: carrier confirms delivery.
- delayed: the carrier missed the promised date, or tracking has not moved for 48
  hours.
- cancelled: order voided and refunded before shipping.

## Looking up an order

Employees look up orders by order number (format NM-XXXXX) or customer email. Always
read the customer the current status and the promised date from the system rather than
estimating from memory.

## Delayed orders

If an order is delayed more than 7 days past the promised date, refund the shipping fee
without being asked, and offer 10 percent off the order as goodwill if the customer had
to come in about it. Both actions are logged on the order.

## Lost packages

Tracking showing no movement for 10 days, or a delivery the customer disputes, opens a
carrier claim from the OMS. Replace or refund the order immediately; the store does not
make the customer wait for the carrier claim to resolve.

## Store pickup

Pickup orders are held for 7 days, then cancelled and refunded automatically. ID matching
the order name is required at pickup.

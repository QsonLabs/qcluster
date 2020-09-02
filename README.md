# qcluster
Quick Cluster - a simple service registry for failover and replication

# Context and Problem

In modern services it is expected that failover, replication or both are provided out of the box. Especially in a distributed cloud architecture, where nodes can be spun up on demand, registering new services is an essential part of ensuring both scalabiity and reliability. There are several robust solutions for service management that include Apache Zookeepr, Istio Serice Mesh, and Linkerd. Each of these either implement a proxy for traffic or have complex architecture requirements. Sometimes a service does not want the full suite of features and needs a lightwieght way to handle failmover.

# Solution

Qcluster is intended to be a lightweight service that enables failover and replication for services that do not need the heavy lift associated with other service mesh tools. This can be achieved by:

- ensuring that qcluster clients can run in a masterless environement
- allowing for a master-minion model as well, which may benefit stateful applicatations
- encouracing self registration 
- enabling built in metrics
- api access and client SDKs


# Issues and Considerations


# When to use this Qcluster vs other mesh


# Examples




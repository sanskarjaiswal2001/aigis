# Network Interface Issues

## Symptoms
- `network` check at WARN or CRITICAL — interface down
- SSH connection drops or refuses
- Services unreachable from outside

## Diagnosis

```bash
# Interface status
ip -br addr show
ip link show

# Routing table
ip route show

# Check if interface is up
ip link show eth0 | grep -w UP

# DNS resolution
resolvectl status
cat /etc/resolv.conf
dig google.com

# Active connections
ss -tulnp

# Listening ports
ss -tlnp

# Firewall rules
iptables -L -n -v
nft list ruleset   # if using nftables
ufw status verbose # if using ufw

# Test connectivity
ping -c 4 8.8.8.8
traceroute 8.8.8.8
curl -I https://google.com
```

## Fixes

### Bring interface back up
```bash
ip link set eth0 up
# or via NetworkManager
nmcli device connect eth0
# or systemd-networkd
networkctl up eth0
```

### Restart networking service
```bash
# NetworkManager
systemctl restart NetworkManager

# systemd-networkd
systemctl restart systemd-networkd

# Traditional networking (Debian)
systemctl restart networking
```

### Renew DHCP lease
```bash
dhclient -r eth0   # release
dhclient eth0      # renew
# or
nmcli device reapply eth0
```

### Fix DNS issues
```bash
# Flush DNS cache
resolvectl flush-caches
# or
systemd-resolve --flush-caches

# Test with explicit DNS
dig @8.8.8.8 google.com

# Restart resolved
systemctl restart systemd-resolved
```

### Open a blocked port (ufw)
```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw reload
```

### Fix iptables blocking traffic
```bash
# Allow established connections
iptables -I INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow specific port
iptables -I INPUT -p tcp --dport 8080 -j ACCEPT

# Save rules
iptables-save > /etc/iptables/rules.v4
```

### Interface not found after reboot
```bash
# Check if driver loaded
lspci | grep -i network
lsmod | grep e1000  # replace with actual driver name
modprobe e1000

# Persistent interface naming
ls /etc/systemd/network/
cat /etc/network/interfaces
```

## Prevention
- Pin interface names with udev rules or systemd .link files to avoid `eth0` becoming `ens3`
- Keep firewall rules in version control or backup `/etc/iptables/`
- Set up monitoring for interface state changes

# Manager node

All this is about the manager node, central to DSAF, that allows human and automated operators to interact with distributed nodes.


## How to run

fades -r requirements.txt main.py


# How it works

It starts to coupled servers: one for interface with users, other to interface with devices.

The server for the devices is exposed in port 7739 (the devices know this), and dialog there is based on a binary protocol.

The server for users is exposed in port 5000, and dialog is based on HTTP REST(ish) endpoints:

- `GET /v1/device/`: List all devices names
```
$ curl -s http://localhost:5000/v1/device/ | jq .
[
  "testdev"
]
```

- `GET /v1/device/<string:name>/health`: Return the latest health indication from the device
```
$ curl -s http://localhost:5000/v1/device/testdev/health | jq .
{
  "last_report_content": {
    "configured": true,
    "current_time": [2000, 1, 1, 0, 39, 7, 5, 1],
    "mem_free": 7936
  },
  "last_report_date": "Wed, 10 Sep 2025 14:23:18 GMT",
  "name": "testdev"
}
```

- `POST /v1/device/<string:name>/code`: Set code to be executed in the device
```
$ curl -s -X POST --data-binary @test-ej-code.py  http://localhost:5000/v1/device/testdev/code
{
  "setup": {
    "delay_ms": 10,
    "error": null
  },
  "started": {
    "delay_ms": 3,
    "error": null
  },
  "stopped": {
    "delay_ms": 3,
    "error": null
  }
}
```

- `GET /v1/device/<string:name>/code`: Return the code that is being executed in the device
```
FIXME
```


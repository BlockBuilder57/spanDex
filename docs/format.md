| name | type | desc |
|------|------|------|
| Message Type | u8 | Determines the type of the message |
| Color | u8 x3 | Color as RGB bytes |
| Position | u32 x2 | Pixel position |


Message types
MSB means compressed (gzip?)
- 0b0000000: C ping
- 0b0000001: C put pixel
- 0b0000010: C get tile
- 0b1000000: S pong
- 0b1000001: S send config
- 0b1000010: S send tile
- 0b1000011: S send pixel
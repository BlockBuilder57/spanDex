| name | type | desc |
|------|------|------|
| Message Type | u8 | Determines the type of the message |
| Color | u8 x4 | Color as RGBA bytes |
| Position | u32 x2 | Pixel position |


Message types
MSB means compressed (gzip?)
- 0b0000000: C ping
- 0b0001001: C put pixel
- 0b0001010: C put pixel batch
- 0b0010001: C get tile
- 0b1000000: S pong
- 0b1000001: S send config
- 0b1001001: S send pixel
- 0b1001010: S send pixel batch
- 0b1010001: S send tile
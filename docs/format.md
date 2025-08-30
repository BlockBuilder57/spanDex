| name | type | desc |
|------|------|------|
| Message Type | u8 | Determines the type of the message |
| Color | u8 x4 | Color as RGBA bytes |
| Position | u32 x2 | Pixel position |

Message types are split into two parts of 3 bits, with the highest two bits signifying gzip compression and client (0) and server (1) origin. The first of the parts is a category, and the last being the method in that category.

Categories (client/server respectively)
- `0b--000---` - System (SYS)
  - `0b--^^^000` - Ping | Pong
  - `0b--^^^001` - N/A | Config
- `0b--001---` - Pixels (PIX)
  - `0b--^^^000` - Put | Send
  - `0b--^^^001` - Put Batch | Send Batch
  - `0b--^^^010` - Put Rect | Send Rect
  - `0b--^^^011` - Put Clear | Send Clear
  - `0b--^^^100` - Put Clear Rect | Send Clear Rect
- `0b--010---` - Tiles (TIL)
  - `0b--^^^000` - Get | Send
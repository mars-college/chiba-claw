# Resource Examples

These JSON objects are the payloads expected by `upsert-resource.mjs`.

## Playlist

```json
{
  "id": "pl-example",
  "title": "Example Playlist",
  "artist": "chiba-claw",
  "description": "Example playlist",
  "items": [
    { "index": 0, "mediaId": "m-upload-123" },
    { "index": 1, "mediaId": "m-upload-456", "durationSec": 12 }
  ]
}
```

## Block

```json
{
  "id": "bl-example",
  "title": "Example Block",
  "mode": "loop",
  "items": [
    { "index": 0, "playlistId": "pl-example" }
  ]
}
```

## Channel

```json
{
  "id": "ch-example",
  "number": "501",
  "name": "Example Channel",
  "blockIds": ["bl-example"]
}
```

## Profile

```json
{
  "id": "pr-example",
  "title": "Example Profile",
  "defaults": {
    "mode": "gallery"
  },
  "defaultTarget": {
    "kind": "channel",
    "id": "ch-example"
  },
  "nodes": [
    {
      "nodeId": "lower-west-2",
      "target": {
        "kind": "playlist",
        "id": "pl-example"
      },
      "launch": {
        "mode": "gallery"
      }
    }
  ]
}
```

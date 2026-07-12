# Gmail Integration Tools Description

This document defines guidelines for the OpenClaw agent planner on when and how to use the Gmail tool suite.

## Gmail Tools List

1. **`gmail.search`**
   - **When to use**: To find specific emails or threads using native search operators.
   - **Search Operators Guide**:
     - Filter by sender: `from:john`
     - Filter by recipient: `to:me` or `to:hr`
     - Check unread: `is:unread`
     - Check importance: `label:important`
     - Time frames: `newer_than:7d`, `older_than:30d`
     - Attachments: `has:attachment`, `filename:pdf`
   - **Pagination**: Use `limit` (default: 10) and pass `page_token` to load the next page of search results.

2. **`gmail.read`**
   - **When to use**: To load the full contents or basic information of a specific email message using its `message_id`.
   - **Format styles**:
     - `minimal` (default): Returns only essential text-based fields (`from`, `subject`, `body`, `date`, `snippet`). Use this by default for general LLM context to save token space.
     - `full`: Returns complete headers, CC/BCC lists, and attachment metadata lists. Use this when you need CC/BCC details or need to find attachment IDs.

3. **`gmail.send`**
   - **When to use**: To write and send a brand new email message.
   - **Fields**: Supports multiple recipients, CC/BCC lists, and attachments (via absolute local file paths).
   - **Body format**: You can supply `text_body` (plain text) and/or `html_body` (rich text).

4. **`gmail.reply`**
   - **When to use**: To reply to an existing email message or thread.
   - **Parameters**: 
     - Pass `message_id` to reply to a specific email (preferred).
     - Pass `thread_id` to reply to a thread; the tool will automatically resolve the latest message in that thread and attach the reply headers correctly.

5. **`gmail.download_attachment`**
   - **When to use**: To fetch raw file bytes for a specific attachment and write them to a local folder.
   - **Flow**: First call `gmail.read(message_id, format="full")` to obtain the `attachment_id` and `filename`, then call `gmail.download_attachment(message_id, attachment_id, output_dir)`.

---

## Example Interaction Flows

### Flow A: Checking and Replying to Unread Emails
```
1. gmail.search(query="is:unread", limit=5)
2. gmail.read(message_id="<message_id>", format="minimal")
3. gmail.reply(message_id="<message_id>", body="Thanks, I got your email.")
```

### Flow B: Downloading an Attachment from an Email
```
1. gmail.search(query="from:finance has:attachment", limit=3)
2. gmail.read(message_id="<message_id>", format="full") (extract attachment_id)
3. gmail.download_attachment(message_id="<message_id>", attachment_id="<attachment_id>", output_dir="./downloads")
```

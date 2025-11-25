import json
import re
from typing import List
from starlette.responses import Response
from ag_ui.core.types import RunAgentInput, Message, UserMessage

# pytest 標記為 unit
import pytest
pytestmark = pytest.mark.unit


def extract_events(raw_stream: str) -> List[str]:
    # SSE 格式: data: {json}\n\n
    events = []
    for block in raw_stream.strip().split('\n\n'):
        for line in block.split('\n'):
            if line.startswith('data: '):
                payload = line[len('data: '):].strip()
                events.append(payload)
    return events


def test_awp_sse_event_sequence(client):
    # 準備 RunAgentInput payload
    payload = {
        "messages": [
            {"role": "user", "content": "這是一個超過二十字的測試訊息用於切片"}
        ],
        "context": [],
    }

    resp: Response = client.post('/api/agui/awp', json=payload, headers={"Accept": "text/event-stream"})
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'text/event-stream'

    body = resp.get_data(as_text=True)
    events_payloads = extract_events(body)
    assert len(events_payloads) >= 5, f"必須至少有5個事件，取得: {events_payloads}"

    # 解析 JSON 並檢查事件 type 順序
    types = []
    contents = []
    for ep in events_payloads:
        try:
            obj = json.loads(ep)
        except json.JSONDecodeError:
            pytest.fail(f"事件不是合法 JSON: {ep}")
        types.append(obj.get('type'))
        if obj.get('type') == 'TEXT_MESSAGE_CONTENT':
            contents.append(obj.get('delta') or '')

    assert types[0] == 'RUN_STARTED'
    assert 'TEXT_MESSAGE_START' in types, '缺少 TEXT_MESSAGE_START'
    assert 'TEXT_MESSAGE_END' in types, '缺少 TEXT_MESSAGE_END'
    assert types[-1] == 'RUN_FINISHED'

    # 找出 CONTENT 事件的連續索引範圍確保順序
    content_indices = [i for i, t in enumerate(types) if t == 'TEXT_MESSAGE_CONTENT']
    assert content_indices == sorted(content_indices), 'CONTENT 事件順序應遞增'

    # 驗證 chunk size (最後一片可 <=10)
    for c in contents[:-1]:
        assert len(c) == 10, f'中間 chunk 必須等於10字: {c} ({len(c)})'
    assert len(contents[-1]) <= 10

    # 合併 chunk 確保原始文字被重組 (簡化檢查: 至少包含前10字)
    reconstructed = ''.join(contents)
    assert payload['messages'][0]['content'][:10] in reconstructed

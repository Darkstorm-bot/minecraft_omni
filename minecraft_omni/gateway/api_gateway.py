"""
Minecraft Omni-Builder v3.1 - API Gateway with Approval Workflow
Handles /approve, /discard endpoints and holographic preview coordination.
"""
import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

@dataclass
class PendingBuild:
    """Represents a build awaiting approval"""
    build_id: str
    session_id: str
    player_name: str
    command: str
    tool_calls: List[Dict]
    preview_blocks: List[Dict]  # Ghost blocks for holographic preview
    created_at: float
    status: str = 'pending'  # pending, approved, discarded, expired
    expires_at: float = 0

    def __post_init__(self):
        if not self.expires_at:
            self.expires_at = self.created_at + 300  # 5 minute timeout

class ApprovalWorkflowManager:
    """Manages build approval/discarding workflow"""
    
    def __init__(self):
        self.pending_builds: Dict[str, PendingBuild] = {}
        self.build_history: List[PendingBuild] = []
        self.cleanup_task = None

    async def start(self):
        """Start background cleanup task"""
        self.cleanup_task = asyncio.create_task(self._cleanup_expired())

    async def stop(self):
        """Stop the manager"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_expired(self):
        """Remove expired pending builds"""
        while True:
            try:
                now = datetime.now().timestamp()
                expired = [bid for bid, pb in self.pending_builds.items() 
                          if pb.expires_at < now and pb.status == 'pending']
                for bid in expired:
                    self.pending_builds[bid].status = 'expired'
                    self.build_history.append(self.pending_builds.pop(bid))
                    logger.info(f"Build {bid} expired")
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break

    def create_pending_build(self, session_id: str, player_name: str, command: str,
                            tool_calls: List[Dict], preview_blocks: List[Dict]) -> str:
        """Create a new pending build requiring approval"""
        build_id = str(uuid.uuid4())[:8]
        now = datetime.now().timestamp()
        
        pb = PendingBuild(
            build_id=build_id,
            session_id=session_id,
            player_name=player_name,
            command=command,
            tool_calls=tool_calls,
            preview_blocks=preview_blocks,
            created_at=now
        )
        self.pending_builds[build_id] = pb
        logger.info(f"Created pending build {build_id} for {player_name}")
        return build_id

    def approve_build(self, build_id: str) -> Optional[PendingBuild]:
        """Approve a pending build"""
        if build_id not in self.pending_builds:
            return None
        pb = self.pending_builds[build_id]
        if pb.status != 'pending':
            return None
        pb.status = 'approved'
        self.build_history.append(self.pending_builds.pop(build_id))
        logger.info(f"Build {build_id} approved")
        return pb

    def discard_build(self, build_id: str) -> Optional[PendingBuild]:
        """Discard a pending build"""
        if build_id not in self.pending_builds:
            return None
        pb = self.pending_builds[build_id]
        if pb.status != 'pending':
            return None
        pb.status = 'discarded'
        self.build_history.append(self.pending_builds.pop(build_id))
        logger.info(f"Build {build_id} discarded")
        return pb

    def get_build_status(self, build_id: str) -> Optional[Dict]:
        """Get status of a build"""
        if build_id in self.pending_builds:
            pb = self.pending_builds[build_id]
            return {
                'build_id': pb.build_id,
                'status': pb.status,
                'command': pb.command,
                'created_at': pb.created_at,
                'expires_at': pb.expires_at
            }
        # Check history
        for pb in self.build_history:
            if pb.build_id == build_id:
                return {
                    'build_id': pb.build_id,
                    'status': pb.status,
                    'command': pb.command,
                    'created_at': pb.created_at
                }
        return None

class HolographicPreviewRenderer:
    """Generates ghost block data for client-side holographic preview"""
    
    @staticmethod
    def generate_preview(tool_calls: List[Dict], offset_y: int = 0) -> List[Dict]:
        """Convert tool calls to ghost block format for client rendering"""
        preview_blocks = []
        for call in tool_calls:
            if call.get('tool') == 'place_block':
                args = call.get('arguments', {})
                preview_blocks.append({
                    'x': args.get('x', 0),
                    'y': args.get('y', 0) + offset_y,
                    'z': args.get('z', 0),
                    'block': args.get('block_type', 'stone'),
                    'properties': args.get('properties', {}),
                    'alpha': 0.5,  # Semi-transparent for ghost effect
                    'outline': True
                })
        return preview_blocks

    @staticmethod
    def generate_outline_boxes(preview_blocks: List[Dict]) -> List[Dict]:
        """Generate bounding box outlines for preview"""
        boxes = []
        for block in preview_blocks:
            boxes.append({
                'minX': block['x'] - 0.5,
                'minY': block['y'] - 0.5,
                'minZ': block['z'] - 0.5,
                'maxX': block['x'] + 0.5,
                'maxY': block['y'] + 0.5,
                'maxZ': block['z'] + 0.5,
                'color': '#00FF00',  # Green outline
                'lineWidth': 2
            })
        return boxes

class APIGateway:
    """Main API Gateway handling HTTP/WebSocket connections"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.approval_manager = ApprovalWorkflowManager()
        self.preview_renderer = HolographicPreviewRenderer()
        self.websocket_clients: Dict[str, web.WebSocketResponse] = {}
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_post('/api/v1/build/submit', self.handle_build_submit)
        self.app.router.add_post('/api/v1/build/{build_id}/approve', self.handle_approve)
        self.app.router.add_post('/api/v1/build/{build_id}/discard', self.handle_discard)
        self.app.router.add_get('/api/v1/build/{build_id}/status', self.handle_status)
        self.app.router.add_get('/ws/{session_id}', self.handle_websocket)

    async def handle_build_submit(self, request: web.Request) -> web.Response:
        """Submit a build for approval"""
        try:
            data = await request.json()
            session_id = data.get('session_id')
            player_name = data.get('player_name')
            command = data.get('command')
            tool_calls = data.get('tool_calls', [])
            
            if not all([session_id, player_name, command]):
                return web.json_response({'error': 'Missing required fields'}, status=400)
            
            # Generate holographic preview
            preview_blocks = self.preview_renderer.generate_preview(tool_calls)
            
            # Create pending build
            build_id = self.approval_manager.create_pending_build(
                session_id=session_id,
                player_name=player_name,
                command=command,
                tool_calls=tool_calls,
                preview_blocks=preview_blocks
            )
            
            # Notify client via WebSocket if connected
            await self._notify_client(session_id, {
                'type': 'build_submitted',
                'build_id': build_id,
                'preview_blocks': preview_blocks,
                'outlines': self.preview_renderer.generate_outline_boxes(preview_blocks)
            })
            
            return web.json_response({
                'build_id': build_id,
                'status': 'pending',
                'message': 'Build submitted for approval. Use /approve or /discard in chat.'
            })
        except Exception as e:
            logger.error(f"Build submit error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_approve(self, request: web.Request) -> web.Response:
        """Approve a pending build"""
        build_id = request.match_info['build_id']
        pb = self.approval_manager.approve_build(build_id)
        
        if not pb:
            return web.json_response({'error': 'Build not found or already processed'}, status=404)
        
        # Execute the build via WebSocket to Minecraft client
        await self._notify_client(pb.session_id, {
            'type': 'build_approved',
            'build_id': build_id,
            'tool_calls': pb.tool_calls
        })
        
        return web.json_response({
            'build_id': build_id,
            'status': 'approved',
            'message': 'Build approved and executing...'
        })

    async def handle_discard(self, request: web.Request) -> web.Response:
        """Discard a pending build"""
        build_id = request.match_info['build_id']
        pb = self.approval_manager.discard_build(build_id)
        
        if not pb:
            return web.json_response({'error': 'Build not found or already processed'}, status=404)
        
        # Clear preview on client
        await self._notify_client(pb.session_id, {
            'type': 'build_discarded',
            'build_id': build_id
        })
        
        return web.json_response({
            'build_id': build_id,
            'status': 'discarded',
            'message': 'Build discarded'
        })

    async def handle_status(self, request: web.Request) -> web.Response:
        """Get build status"""
        build_id = request.match_info['build_id']
        status = self.approval_manager.get_build_status(build_id)
        
        if not status:
            return web.json_response({'error': 'Build not found'}, status=404)
        
        return web.json_response(status)

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections from Minecraft clients"""
        session_id = request.match_info['session_id']
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_clients[session_id] = ws
        logger.info(f"WebSocket connected: {session_id}")
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_ws_message(session_id, data, ws)
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WS error: {ws.exception()}")
        finally:
            del self.websocket_clients[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")
        
        return ws

    async def _handle_ws_message(self, session_id: str, data: Dict, ws: web.WebSocketResponse):
        """Handle incoming WebSocket messages"""
        msg_type = data.get('type')
        
        if msg_type == 'heartbeat':
            await ws.send_json({'type': 'pong'})
        elif msg_type == 'build_complete':
            logger.info(f"Build completed: {data.get('build_id')}")
        elif msg_type == 'build_error':
            logger.error(f"Build error: {data.get('error')}")

    async def _notify_client(self, session_id: str, message: Dict):
        """Send message to specific client"""
        if session_id in self.websocket_clients:
            try:
                await self.websocket_clients[session_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to notify client {session_id}: {e}")

    async def start(self):
        """Start the API gateway"""
        await self.approval_manager.start()
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"API Gateway started on http://{self.host}:{self.port}")

    async def stop(self):
        """Stop the API gateway"""
        await self.approval_manager.stop()
        await self.app.shutdown()

# Example usage
if __name__ == "__main__":
    async def main():
        gateway = APIGateway(port=8080)
        await gateway.start()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            await gateway.stop()

    # asyncio.run(main())

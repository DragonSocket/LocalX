from __future__ import annotations
from typing import Optional, Callable
from src.controller.models import UserInfo, Message, HistoryState, SystemState, StateData
from src.controller.state import StateManager
from src.controller.formatter import TextFormatter
from src.interfaces import Transport, Storage
from src.controller.utils import validate_message

# Export state structures at module level for test compatibility
StateData = StateData  # type alias

class ChatController:
    # Class factory method for tests that pass state_manager directly
    _state_manager_factory = lambda: StateManager()
    def __init__(self, name: str, host: Optional[str] = None, port: Optional[int] = None, storage: Optional[Storage] = None, transport: Optional[Transport] = None):
        self._user_info = UserInfo(name, host, port)
        self._state_manager = StateManager()
        self._state_manager._init_state(self._user_info)
        self._formatter = TextFormatter()
        self._storage = storage
        self._transport = transport

    _create_state_manager = classmethod(lambda cls: ChatController._state_manager_factory())

    @property
    def storage(self) -> Optional[Storage]:
        return self._storage

    @property
    def transport(self) -> Optional[Transport]:
        return self._transport

    @property
    def state_manager(self) -> StateManager: return self._state_manager

    async def load_history(self, limit: int = 100) -> None:
        if self._storage:
            try:
                history = await self._storage.fetch_history(limit)
                self._state_manager.initialize_with_history(history)
                # Also call _init_state with stored user info from history or existing setup
                if not hasattr(self._state_manager, 'info'):
                    default_user = UserInfo("default", None, None)
                    self._state_manager._init_state(default_user)
            except Exception as e: self._state_manager.set_error(str(e))

    async def get_history(self, limit: Optional[int] = None) -> list[tuple[str, str, int]]:
        """Fetch chat history from storage.
        
        Args:
            limit: Maximum number of messages to return. If None or 0+, 
                   passes through to Storage (which interprets 0 as "all").
            
        Returns:
            List of (sender_id, text, timestamp) tuples, oldest first.
            
        Behavior depends on Storage implementation:
            - InMemoryStorage: limit=0 returns all messages
            - SqliteStorage: limit=0 returns up to 1M messages (effectively all)
        
        """
        if self._storage is None:
            return []
        
        try:
            # Pass limit directly to storage - implementations handle their own semantics
            history = await self._storage.fetch_history(limit)
            
            # Normalize result to list of tuples (should already be tuples from storage)
            return history
            
        except Exception as e:
            self._state_manager.set_error(f"Error fetching history: {e}")
            return []

    async def send_message(self, message: str, peer: Optional[str] = None) -> bool:
        """Send a message to the connected peer via Transport.
        
        Args:
            message: Raw message text to send.
            peer: Optional peer identifier for targeting specific peer.
            
        Returns:
            True if message sent successfully, False otherwise.
            
        Behavior:
            - Validates message content (empty, null, length, control chars)
            - Catches validation errors and reports via state_manager
            - Formats message using TextFormatter
            - Sends via Transport.send() if transport exists
            - Returns True only on successful send through Transport
            
        Notes:
            - If transport is None/unconfigured, returns False (no network to send to)
            - Validation failures caught and reported as errors via state_manager
        """
        try:
            # Step 1: Validate the message content first
            is_valid, _ = validate_message(message)
            if not is_valid:
                self._state_manager.set_error("Validation failed")
                return False
            
            # Step 2: Update state with the message (for UI history tracking)
            msg_state = self._state_manager.update_message(message, sender="me", receiver=peer)
            
            # Step 3: If transport exists and connected, send via Transport
            if self._transport is None:
                # No transport configured - cannot send anywhere
                return False
            
            # Format message for safe transmission (markdown -> escaped text)
            formatted, escaped = self._formatter.format(message)
            
            # Step 4: Send via Transport interface
            success = await self._transport.send(formatted)
            
            if not success:
                self._state_manager.set_error("Transmission failed")
                return False
            
            return True
            
        except ValueError as e:
            # Validation error - report and return False
            self._state_manager.set_error(str(e))
            return False
            
        except Exception as e:
            # Unexpected transport or send error
            self._state_manager.set_error(f"Send error: {e}")
            return False

    async def save_message(self, msg_text: str, sender: str, timestamp: int = 0) -> bool:
        """Save message to storage with validation.
        
        Returns True if saved successfully, False if not.
        Validates message before attempting storage.
        """
        try:
            # Validate the message content first
            is_valid, _ = validate_message(msg_text)
            if not is_valid:
                raise ValueError("Message invalid")
            
            # Validate sender username
            if not sender or not isinstance(sender, str):
                raise ValueError("Invalid username")
            
            if self._storage:
                await self._storage.save(sender, msg_text, timestamp)
                return True
            
            return False  # No storage configured
        except ValueError as e:
            self._state_manager.set_error(str(e))
            raise
        except Exception as e:
            self._state_manager.set_error(str(e))
            return False

    async def close(self) -> None:
        if self._transport: await self._transport.close()
        if self._storage: await self._storage.close()

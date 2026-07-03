/**
 * Socket.IO client interface for real-time telemetry updates.
 */

let socket = null;

export function connectSocket(onStats) {
  // Initialize relative Socket.IO connection
  socket = io({
    transports: ['websocket']
  });

  socket.on('connect', () => {
    console.log('[Socket] Connected to telemetry backend');
  });

  socket.on('disconnect', () => {
    console.log('[Socket] Disconnected from telemetry backend');
  });

  socket.on('stats', (data) => {
    if (onStats && data) {
      onStats(data);
    }
  });

  return socket;
}

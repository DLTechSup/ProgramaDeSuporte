export interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * O <video> usa `object-fit: contain`, entao o video real fica centralizado
 * dentro do elemento com possiveis barras (letterbox) nas laterais ou em cima/
 * embaixo quando a proporcao da tela do cliente nao bate com a da janela do
 * tecnico. Esta funcao calcula a area real ocupada pelo video e converte a
 * posicao do mouse em coordenadas normalizadas (0..1) relativas a ELA -
 * essenciais para o agente reposicionar o cursor corretamente na tela dele.
 *
 * Pura (recebe o retangulo em vez do elemento DOM) para ser testavel sem jsdom.
 */
export function mapPointToNormalized(
  clientX: number,
  clientY: number,
  rect: Rect,
  videoWidth: number,
  videoHeight: number
): { x: number; y: number } | null {
  if (videoWidth === 0 || videoHeight === 0 || rect.width === 0 || rect.height === 0) {
    return null;
  }

  const elementAspect = rect.width / rect.height;
  const videoAspect = videoWidth / videoHeight;

  let contentWidth = rect.width;
  let contentHeight = rect.height;
  let offsetX = 0;
  let offsetY = 0;

  if (videoAspect > elementAspect) {
    // Barras em cima/embaixo.
    contentHeight = rect.width / videoAspect;
    offsetY = (rect.height - contentHeight) / 2;
  } else {
    // Barras nas laterais.
    contentWidth = rect.height * videoAspect;
    offsetX = (rect.width - contentWidth) / 2;
  }

  const localX = clientX - rect.left - offsetX;
  const localY = clientY - rect.top - offsetY;

  if (localX < 0 || localY < 0 || localX > contentWidth || localY > contentHeight) {
    return null; // Clique caiu na barra de letterbox, fora da tela real do cliente.
  }

  return { x: localX / contentWidth, y: localY / contentHeight };
}

export function mapClientPointToNormalized(clientX: number, clientY: number, video: HTMLVideoElement): { x: number; y: number } | null {
  const rect = video.getBoundingClientRect();
  return mapPointToNormalized(clientX, clientY, rect, video.videoWidth, video.videoHeight);
}

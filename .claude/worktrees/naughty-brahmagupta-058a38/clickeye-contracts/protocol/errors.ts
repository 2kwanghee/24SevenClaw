/**
 * 에러 코드 및 타입 정의
 */

export type ErrorCode =
  | 'AUTH_FAILED'
  | 'LICENSE_EXPIRED'
  | 'LICENSE_LIMIT'
  | 'DOCKER_ERROR'
  | 'ENV_SETUP_FAILED'
  | 'GIT_ERROR'
  | 'CLAUDE_ERROR'
  | 'BUILD_FAILED'
  | 'RESOURCE_LIMIT'
  | 'TIMEOUT'
  | 'UNKNOWN_MESSAGE_TYPE'
  | 'HANDLER_ERROR';

export interface ErrorPayload {
  code: ErrorCode;
  message: string;
  original_message_id?: string;
  recoverable: boolean;
  suggestion?: string;
}

export const ERROR_METADATA: Record<ErrorCode, { recoverable: boolean; description: string }> = {
  AUTH_FAILED: { recoverable: false, description: '인증 실패 - 재등록 필요' },
  LICENSE_EXPIRED: { recoverable: false, description: '라이센스 만료 - 갱신 필요' },
  LICENSE_LIMIT: { recoverable: false, description: '라이센스 한도 초과 - 업그레이드 필요' },
  DOCKER_ERROR: { recoverable: true, description: 'Docker 작업 실패 - 재시도 가능' },
  ENV_SETUP_FAILED: { recoverable: true, description: '환경 구성 실패 - 재시도 가능' },
  GIT_ERROR: { recoverable: true, description: 'Git 작업 실패 - 재시도 가능' },
  CLAUDE_ERROR: { recoverable: true, description: 'Claude 작업 실패 - 재시도 가능' },
  BUILD_FAILED: { recoverable: true, description: '빌드 실패 - 수정 후 재시도' },
  RESOURCE_LIMIT: { recoverable: false, description: '서버 리소스 부족' },
  TIMEOUT: { recoverable: true, description: '작업 시간 초과 - 재시도 가능' },
  UNKNOWN_MESSAGE_TYPE: { recoverable: false, description: '알 수 없는 메시지 타입' },
  HANDLER_ERROR: { recoverable: true, description: '핸들러 처리 오류' },
};

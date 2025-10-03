// detectionLogs/page.tsx
'use client' // Next.js app router에서 이 파일이 클라이언트 컴포넌트임을 선언.
// - React hooks(useState)와 브라우저 API(fetch) 사용 가능해짐.
// - 서버 컴포넌트에서만 가능한 동작(예: 직접 DB쿼리)은 여기서 불가.

import { Pagination, Stack } from '@mui/material' // MUI 컴포넌트: 페이지네이션 UI, Stack 레이아웃
import { useQuery } from '@tanstack/react-query'  // 서버 상태 라이브러리: 데이터 fetching/캐싱/동기화
import { useState } from 'react'                   // React 훅
import { motion } from 'framer-motion'             // 애니메이션 라이브러리

// 기본 내보내기된 페이지 컴포넌트(라우트: /detectionLogs)
export default function DetectionLogsPage() {
  // 현재 페이지 상태(1부터 시작). Pagination의 page와 바인딩됨.
  const [page, setPage] = useState(1)
  // 한 페이지 당 아이템 수(고정값)
  const pageSize = 10

  // Pagination onChange 핸들러: 클릭된 페이지 번호(value)를 상태에 반영
  const handlePageChange = (
    event: React.ChangeEvent<unknown>, // MUI가 주는 이벤트 타입(쓰지 않으므로 unknown OK)
    value: number,                     // 이동할 페이지 번호
  ) => {
    setPage(value)
  }

  // 서버에서 detection logs를 가져오는 비동기 함수
  // - 인자 객체 구조 분해로 page/pageSize를 명시적으로 받음
  const getDetectionLogs = async ({
    page,
    pageSize,
  }: {
    page: number
    pageSize: number
  }) => {
    // 쿼리스트링으로 page, page_size 전달
    const response = await fetch(
      `http://localhost:8000/get_detection_log?page=${page}&page_size=${pageSize}`,
    )
    // 주의: 여기서는 에러 상태(4xx/5xx)를 별도로 처리하지 않고 바로 json 파싱.
    // 필요하면 response.ok 체크 후 throw로 react-query의 error로 넘기기 권장.
    return response.json()
  }

  // react-query 훅: 요청/캐시/로딩상태를 관리
  const { data: getDetectionLogsData } = useQuery({
    // queryKey: 캐시 구분 키. page/pageSize가 바뀌면 다른 캐시 엔트리로 판단해 refetch.
    queryKey: ['get_detection_log', page, pageSize],
    // queryFn: 실제 데이터를 가져오는 함수. 현재 page/pageSize를 클로저로 캡처해 호출.
    queryFn: () => getDetectionLogs({ page, pageSize }),
    // (선택) staleTime, keepPreviousData 등 옵션을 넣으면 UX 개선 가능
  })

  // 전체 페이지 수 계산: total_count / pageSize 올림
  // - 첫 렌더 시 getDetectionLogsData가 undefined일 수 있으므로 ?. 사용
  const pageCount = Math.ceil(getDetectionLogsData?.total_count / pageSize)

  // 개발 편의: 응답 데이터 로깅
  console.log('getDetectionLogsData: ', getDetectionLogsData)

  return (
    // 페이지 전체 컨테이너에 페이드 인/아웃 애니메이션 부여
    <motion.div
      initial={{ opacity: 0 }}                // 첫 진입 시 투명
      animate={{ opacity: 1 }}                // 마운트 후 불투명
      exit={{ opacity: 0 }}                   // 언마운트 시 페이드아웃(라우팅 전환 시 유효)
      transition={{ duration: 0.5 }}          // 애니메이션 시간
      // Tailwind 유틸리티 클래스들: 최소 높이, 배경 그라디언트, 텍스트색, 패딩
      className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white p-4 sm:p-6"
    >
      {/* 리스트 영역: 살짝 위에서 내려오며 페이드인 */}
      <motion.div
        className="space-y-6"                 // 카드 간 수직 간격
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        {/* 응답의 items 배열을 순회 렌더. 옵셔널 체이닝으로 초기 undefined 대비 */}
        {getDetectionLogsData?.items.map((item: any) => (
          <motion.div
            key={item.id}                      // 리스트 렌더 키(안정적 유니크 값 권장)
            className="bg-[#1C1C1E] p-4 rounded-lg shadow-lg"
            whileHover={{ scale: 1.05 }}       // 카드 hover 확대
            transition={{ type: 'spring', stiffness: 300 }}
          >
            {/* 메타 정보 표시 */}
            <p className="text-lg font-semibold">file name: {item.file_name}</p>
            <p>message: {item.message}</p>
            {/* created_at 문자열을 Date로 파싱 후 로컬 문자열로 표시 */}
            <p>created at: {new Date(item.created_at).toLocaleString()}</p>

            {/* 결과 이미지: hover 확대 애니메이션 */}
            <motion.img
              src={`http://localhost:8000/log/${item.result_image}`} // 이미지 경로
              alt={item.file_name}
              className="w-full h-auto rounded-md mt-2 sm:max-w-md"
              whileHover={{ scale: 1.1 }}
              transition={{ type: 'spring', stiffness: 300 }}
            />

            {/* detection 상세 리스트 */}
            <ul className="mt-4 space-y-2">
              {item.detections.map((detection: any, index: number) => (
                <li key={index} className="bg-[#2C2C2E] p-2 rounded-md">
                  <p>class name: {detection.class_name}</p>
                  <p>confidence: {detection.confidence}</p>
                  {/* bbox가 숫자 배열이라 가정하고 join으로 표시 */}
                  <p>bbox: {detection.bbox.join(', ')}</p>
                </li>
              ))}
            </ul>
          </motion.div>
        ))}
      </motion.div>

      {/* 하단 페이지네이션 바: 유리효과 비슷한 배경 + 애니메이션 */}
      <motion.div
        className="bg-[#1C1C1E]/80 backdrop-blur-lg px-4 py-3 rounded-full border border-[#38383A] shadow-xl mt-6 sm:px-6"
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.5 }}
      >
        <Stack spacing={2}>
          <Pagination
            // sx: MUI의 emotion 기반 인라인 스타일(테마 토큰/상태셀렉터 사용 가능)
            sx={{
              '& .MuiPaginationItem-root': {
                color: '#FFFFFF',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                '&.Mui-selected': {
                  backgroundColor: '#0A84FF',
                },
              },
            }}
            page={page}                               // 현재 페이지(상태)
            count={pageCount === 0 ? 1 : pageCount}   // 전체 페이지 수(0 방지 가드)
            boundaryCount={1}                          // 처음/끝 근처 표시 개수
            siblingCount={1}                           // 현재 페이지 주변 표시 개수
            onChange={handlePageChange}                // 페이지 변경 핸들러
            color="primary"                            // 프라이머리 컬러(테마)
            showFirstButton                            // 처음으로 버튼 표시
            showLastButton                             // 마지막으로 버튼 표시
          />
        </Stack>
      </motion.div>
    </motion.div>
  )
}

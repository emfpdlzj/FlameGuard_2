'use client'; 
/**
 * Next.js App Router에서 클라이언트 컴포넌트로 동작하게 하는 지시어.
 * - 브라우저 API(navigator, window 등)와 상호작용하려면 필수.
 */

import { useState, useRef, useEffect } from "react";
/**
 * React 기본 훅:
 * - useState: 상태 관리
 * - useRef: DOM 또는 변경 가능한 객체 참조
 * - useEffect: 마운트/언마운트/의존성 변경 시 부수효과 실행
 */

import { useQuery } from '@tanstack/react-query';
/**
 * TanStack Query:
 * - 서버 요청/캐싱/리트라이/폴링 등을 쉽게 처리
 * - 여기서는 주기적으로 프레임을 서버로 보내는 "polling" 용도
 */

import { motion } from 'framer-motion';
/**
 * framer-motion:
 * - 애니메이션 컴포넌트 제공
 * - motion.div, motion.button 등으로 감싸고 props에 initial/animate/whileHover 등 지정
 */

export default function Home() {
  /**
   * 카메라(비디오 입력) 관련 상태들
   */
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]); // 사용 가능한 카메라 목록
  const [selectedDevice, setSelectedDevice] = useState<string>(""); // 선택된 카메라 deviceId
  const videoRef = useRef<HTMLVideoElement>(null); // <video> DOM 참조
  const [isStreaming, setIsStreaming] = useState(false); // 현재 카메라 스트림 재생 중인지
  const [isPolling, setIsPolling] = useState(false); // 주기적 서버 전송 활성화 여부

  /**
   * 경보음(WebAudio API) 관련 상태/참조
   */
  const [audioPermission, setAudioPermission] = useState(false); // 오디오 권한 획득 여부
  const audioContextRef = useRef<AudioContext | null>(null); // 오디오 컨텍스트(브라우저 오디오 그래프 루트)
  const gainNodeRef = useRef<GainNode | null>(null); // 볼륨 제어용 노드
  const sourceNodeRef = useRef<OscillatorNode | null>(null); // 경보음을 발생시키는 발진기 노드

  /**
   * 마운트 시 1회: 카메라 목록 조회
   * - navigator.mediaDevices.enumerateDevices()로 모든 디바이스를 가져옴
   * - 'videoinput'만 필터링하여 상태에 저장
   * - 첫 카메라를 기본 선택
   */
  useEffect(() => {
    const getDevices = async () => {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        setDevices(videoDevices);
        if (videoDevices.length > 0) {
          setSelectedDevice(videoDevices[0].deviceId);
        }
      } catch (error) {
        console.error('failed to get camera devices:', error);
      }
    };
    getDevices();
  }, []);

  /**
   * 현재 <video> 프레임을 캡처해서 Blob(JPEG)으로 변환
   * - <canvas>를 만들고 drawImage → toBlob 으로 이미지 추출
   * - 비디오가 아직 재생 준비 전(폭/높이 0)인 경우 null 반환
   */
  const captureFrame = async (videoElement: HTMLVideoElement): Promise<Blob | null> => {
    try {
      if (!videoElement.videoWidth || !videoElement.videoHeight) {
        console.log('video size is invalid');
        return null;
      }

      const canvas = document.createElement('canvas');
      canvas.width = videoElement.videoWidth;
      canvas.height = videoElement.videoHeight;

      const ctx = canvas.getContext('2d');
      if (!ctx) return null;

      ctx.drawImage(videoElement, 0, 0);

      // canvas를 JPEG Blob으로 비동기 변환
      return new Promise((resolve) => {
        canvas.toBlob((blob) => {
          resolve(blob || null);
        }, 'image/jpeg');
      });
    } catch (error) {
      console.error('frame capture error:', error);
      return null;
    }
  };

  /**
   * 캡처한 프레임을 서버(/predict_fire)로 전송
   * - FormData에 'file'로 blob 첨부
   * - fetch로 POST → JSON 응답 반환
   * - 스트리밍 중이 아닐 때는 실행하지 않음
   */
  const sendFrameToServer = async () => {
    try {
      if (!videoRef.current || !isStreaming) {
        console.log('video is not playing');
        return null;
      }

      const blob = await captureFrame(videoRef.current);
      if (!blob) {
        console.log('frame capture failed');
        return null;
      }

      const formData = new FormData();
      formData.append('file', blob, 'frame.jpg');

      console.log('sending request to server...');
      const response = await fetch('http://localhost:8000/predict_fire', {
        method: 'POST',
        body: formData,
      });

      // 서버에서 JSON 형태로 응답이 온다고 가정
      const data = await response.json();
      console.log('server response:', data);
      return data;
    } catch (error) {
      console.error('server request error:', error);
      return null;
    }
  };

  /**
   * TanStack Query로 주기적 폴링 설정
   * - enabled: true일 때만 동작
   * - refetchInterval: 5초마다 sendFrameToServer 호출
   * - retry: false → 실패 시 자동 재시도 안 함
   * - queryKey: 캐시 키
   */
  const { data: predictionData } = useQuery({
    queryKey: ['fireDetection'],
    queryFn: sendFrameToServer,
    enabled: isPolling && isStreaming, // 스트리밍+폴링 둘 다 켜져야 실행
    refetchInterval: 5000,             // 5초마다 한 번
    retry: false,
  });

  /**
   * 오디오 컨텍스트 초기화(권한 요청 포함)
   * - 모바일/사파리에서는 사용자 인터랙션(클릭 등) 후 resume 필요
   * - 허용 시 audioContextRef 생성 및 상태 업데이트
   */
  const initAudioContext = async () => {
    try {
      if (!audioPermission) {
        const userConsent = window.confirm("fire alarm requires audio permission. allow?");
        if (!userConsent) {
          return false;
        }

        // Safari 호환 위해 webkitAudioContext 고려
        const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
        audioContextRef.current = new AudioContext();

        // iOS Safari 등 특정 환경에서 초기 상태가 'suspended'일 수 있음
        if (audioContextRef.current.state === 'suspended') {
          await audioContextRef.current.resume();
        }

        setAudioPermission(true);
        return true;
      }
      return true;
    } catch (error) {
      console.error("audio initialization error:", error);
      alert("audio initialization failed.");
      return false;
    }
  };

  /**
   * 경보음 정지:
   * - 발진기(oscillator)와 게인 노드를 종료/해제
   */
  const stopAlertSound = () => {
    if (sourceNodeRef.current) {
        sourceNodeRef.current.stop();
        sourceNodeRef.current.disconnect();
    }
    if (gainNodeRef.current) {
        gainNodeRef.current.disconnect();
    }
  };

  /**
   * 경보음 재생:
   * - OscillatorNode(사톱 파형) 생성, gain으로 볼륨 제어
   * - frequency를 ramp로 변화시켜 경보음 느낌
   * - start()로 재생 시작
   */
  const playAlertSound = () => {
    if (!audioContextRef.current) return;
    stopAlertSound(); // 중복 재생 대비

    const oscillator = audioContextRef.current.createOscillator();
    gainNodeRef.current = audioContextRef.current.createGain();

    oscillator.type = 'sawtooth'; // 사톱파(경보음 느낌)
    oscillator.frequency.setValueAtTime(440, audioContextRef.current.currentTime);

    // 간단한 주파수 변조(440Hz → 880Hz → 440Hz)
    oscillator.frequency.setValueAtTime(440, audioContextRef.current.currentTime);
    oscillator.frequency.linearRampToValueAtTime(880, audioContextRef.current.currentTime + 0.5);
    oscillator.frequency.linearRampToValueAtTime(440, audioContextRef.current.currentTime + 1);

    // 볼륨(0.5)
    gainNodeRef.current.gain.setValueAtTime(0.5, audioContextRef.current.currentTime);

    oscillator.connect(gainNodeRef.current);
    gainNodeRef.current.connect(audioContextRef.current.destination);

    oscillator.start();
    sourceNodeRef.current = oscillator; // stop 시 접근 가능하도록 ref에 저장
  };

  /**
   * 예측 결과가 갱신될 때마다 감시:
   * - 서버 응답의 message가 "fire detected"면 경보음 + 화면 플래시 + 토스트 알림
   * - 일정 시간 후 자동 제거
   */
  useEffect(() => {
    if (predictionData?.message === "fire detected") {
      // 경보음 재생
      playAlertSound();
      
      // 화면 전체 플래시용 오버레이 요소 생성
      const flashOverlay = document.createElement('div');
      flashOverlay.className = 'fixed inset-0 pointer-events-none animate-screenFlash';
      document.body.appendChild(flashOverlay);
      
      // 간단한 토스트 알림 생성(아이콘+텍스트)
      const alertElement = document.createElement('div');
      alertElement.innerHTML = `
        <div class="flex items-center gap-3">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"
               viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2c0 6-8 7.5-8 14a8 8 0 0 0 16 0c0-6.5-8-8-8-14z"/>
          </svg>
          <div>
            <div class="font-semibold mb-0.5">fire detected</div>
            <div class="text-sm opacity-90">fire detected. please check immediately.</div>
          </div>
        </div>
      `;
      alertElement.className = `
        fixed bottom-6 right-6 p-4
        bg-red-500/90 text-white
        rounded-xl
        shadow-lg
        backdrop-blur-md
        max-w-[400px] z-[9999]
        font-sans
        animate-slideIn animate-pulse animate-flashBorder
      `;
      document.body.appendChild(alertElement);

      // 10초 후 자동 제거(사라지는 애니메이션 포함)
      const timeout = setTimeout(() => {
        if (document.body.contains(alertElement)) {
          alertElement.classList.remove('animate-slideIn');
          alertElement.classList.add('animate-slideOut');
          flashOverlay.remove();
          setTimeout(() => {
            document.body.removeChild(alertElement);
          }, 500);
        }
      }, 10000);

      // cleanup: 의존성 변경/언마운트 시 제거
      return () => {
        clearTimeout(timeout);
        if (document.body.contains(alertElement)) {
          document.body.removeChild(alertElement);
        }
        if (document.body.contains(flashOverlay)) {
          flashOverlay.remove();
        }
      };
    }
  }, [predictionData]);

  /**
   * 예측 시작:
   * - 오디오 권한/컨텍스트 초기화
   * - 선택된 카메라로 getUserMedia → <video>에 스트림 연결 → 재생
   * - isStreaming / isPolling true로 전환하여 폴링 시작
   */
  const startPredict = async () => {
    try {
      const audioInitialized = await initAudioContext();
      if (!audioInitialized) {
        console.log('audio permission denied');
        return;
      }

      // 선택된 카메라 장치로 비디오 스트림 요청
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: selectedDevice },
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setIsStreaming(true);
        setIsPolling(true);
        console.log('streaming started');
      }
    } catch (error) {
      console.error('camera access error:', error);
    }
  };

  /**
   * 예측 중지:
   * - 경보음 정지
   * - 비디오 트랙 정지 및 스트림 해제
   * - 폴링 중지
   */
  const stopPredict = () => {
    stopAlertSound();
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
      tracks.forEach(track => track.stop()); // 카메라/마이크 등 모든 트랙 정지
      videoRef.current.srcObject = null;     // 영상 요소에서 분리
      setIsStreaming(false);
      setIsPolling(false); // 폴링 중단
    }
  };

  // 디버그: 최근 예측 결과 콘솔 출력
  console.log('fire detection result:', predictionData);

  /**
   * 렌더링:
   * - 카메라 선택 드롭다운
   * - 시작/중지 버튼
   * - 로그 페이지 이동 버튼
   * - 비디오 프리뷰
   * - framer-motion으로 간단한 페이드/스케일 애니메이션
   */
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-gray-900 text-white">
      <div className="space-y-4 w-full max-w-md">
        {/* 카메라 선택 셀렉트 박스 */}
        <motion.select
          value={selectedDevice}
          onChange={(e) => setSelectedDevice(e.target.value)}
          className="w-full border border-gray-700 p-2 rounded-md shadow-sm bg-gray-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          {devices.map((device) => (
            <option key={device.deviceId} value={device.deviceId}>
              {device.label || `Camera ${device.deviceId.slice(0, 5)}...`}
            </option>
          ))}
        </motion.select>

        {/* 시작/중지 토글 버튼 */}
        {!isStreaming ? (
          <motion.button
            onClick={startPredict}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            Start Stream
          </motion.button>
        ) : (
          <motion.button
            onClick={stopPredict}
            className="w-full px-4 py-2 bg-red-600 text-white rounded-md shadow-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            Stop Stream
          </motion.button>
        )}

        {/* 탐지 로그 페이지 이동(Next 라우팅을 더 권장하지만 간단히 location 사용) */}
        <motion.button
          onClick={() => window.location.href = '/detectionLogs'}
          className="w-full px-4 py-2 bg-green-600 text-white rounded-md shadow-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          View Detection Logs
        </motion.button>
      </div>

      {/* 비디오 프리뷰(카메라 스트림 바인딩) */}
      <motion.video
        ref={videoRef}
        autoPlay       // 자동 재생
        playsInline    // iOS 등에서 전체화면 강제 방지
        className="w-full max-w-md h-auto mt-4 rounded-md shadow-lg bg-black"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      />
    </div>
  );
}

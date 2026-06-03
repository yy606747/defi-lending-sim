import { afterEach, vi } from 'vitest'
import { config } from '@vue/test-utils'

vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
  },
}))

const canvasContext = {
  clearRect: vi.fn(),
  beginPath: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  stroke: vi.fn(),
}

Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
  configurable: true,
  value: () => canvasContext,
})

vi.stubGlobal('requestAnimationFrame', vi.fn(() => 1))
vi.stubGlobal('cancelAnimationFrame', vi.fn())

config.global.stubs = {
  RouterLink: {
    props: ['to'],
    template: '<a :href="typeof to === `string` ? to : to.path"><slot /></a>',
  },
  RouterView: {
    template: '<div data-test="router-view" />',
  },
  Transition: {
    props: ['name', 'mode'],
    template: '<slot />',
  },
}

afterEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

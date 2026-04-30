import sys
import asyncio
import pyperclip
import re
import subprocess
from playwright.async_api import async_playwright

# ========== CẤU HÌNH UI/MÀU SẮC ==========
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ========== SELECTOR TỪ DEEPSEEK ==========
STOP_BUTTON_SELECTOR = 'button[role="button"]:has(svg path[d*="M6.14929"])'
COPY_BUTTON_SELECTOR = 'div[role="button"]:has(svg path[d*="M9.67272"])'

# ========== LỚP QUẢN LÝ AGENT DEEPSEEK ==========
class DeepSeekAgent:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def connect(self):
        print(f"{Colors.CYAN}[HỆ THỐNG] Đang kết nối với Chrome CDP...{Colors.ENDC}")
        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")
            self.context = self.browser.contexts[0]
            
            # Tìm tab DeepSeek
            for p in self.context.pages:
                if "deepseek.com" in p.url:
                    self.page = p
                    break
            if not self.page and self.context.pages:
                self.page = self.context.pages[0]
                
            if not self.page:
                print(f"{Colors.RED}[LỖI] Không tìm thấy tab nào. Hãy mở https://chat.deepseek.com{Colors.ENDC}")
                sys.exit(1)
                
            await self.page.bring_to_front()
            print(f"{Colors.GREEN}[HỆ THỐNG] Đã kết nối thành công với phiên DeepSeek!{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}[LỖI KẾT NỐI] {e}{Colors.ENDC}")
            print("Đảm bảo bạn đã chạy Chrome với lệnh: chrome.exe --remote-debugging-port=9222")
            sys.exit(1)

    async def send_prompt(self, prompt):
        """Gửi tin nhắn và CHỈ dùng nút Copy để lấy kết quả"""
        print(f"\n{Colors.BLUE}[AGENT] Đang gửi yêu cầu cho DeepSeek...{Colors.ENDC}")
        
        # Gửi text
        textarea = self.page.locator('textarea').first
        await textarea.wait_for(state="visible", timeout=5000)
        await textarea.fill("")
        await asyncio.sleep(0.2)
        await textarea.fill(prompt)
        await self.page.keyboard.press("Enter")
        
        # Chờ phản hồi
        await self._wait_for_response()
        
        # Lấy kết quả qua nút Copy
        return await self._copy_via_button()

    async def _wait_for_response(self, timeout=120000):
            print(f"{Colors.CYAN}[AGENT] Đang chờ DeepSeek suy nghĩ và gõ câu trả lời...{Colors.ENDC}")
            try:
                stop_btn = self.page.locator(STOP_BUTTON_SELECTOR).first
                
                # 1. Đợi nút Stop xuất hiện (Báo hiệu bắt đầu generate)
                # Dùng try-except vì đôi khi mạng nhanh, nó gen xong trước khi ta kịp bắt
                try:
                    await stop_btn.wait_for(state="visible", timeout=3000)
                except Exception:
                    pass
                
                # 2. Đợi nút Stop biến mất (Báo hiệu generate xong)
                await stop_btn.wait_for(state="hidden", timeout=timeout)
                
                # Chờ thêm 2 giây để UI render xong nút Copy cho tin nhắn mới nhất
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"{Colors.RED}[CẢNH BÁO] Lỗi theo dõi DOM ({e}), vẫn tiếp tục copy...{Colors.ENDC}")

    async def _copy_via_button(self, max_retries=3):
        for attempt in range(max_retries):
            try:
                # Lấy TẤT CẢ các nút Copy hiện có trên màn hình
                copy_btns = self.page.locator(COPY_BUTTON_SELECTOR)
                count = await copy_btns.count()
                
                if count > 0:
                    # Lấy nút Copy CUỐI CÙNG (thuộc về tin nhắn mới nhất)
                    last_copy_btn = copy_btns.nth(count - 1)
                    
                    # Xóa bộ nhớ tạm trước khi copy để tránh dính data cũ
                    pyperclip.copy("") 
                    
                    # Click nút copy
                    await last_copy_btn.click()
                    await asyncio.sleep(1.5)
                    
                    new_clipboard = pyperclip.paste()
                    if new_clipboard and len(new_clipboard) > 10:
                        return new_clipboard
                        
            except Exception as e:
                print(f"{Colors.YELLOW}[CẢNH BÁO] Lỗi click copy lần {attempt+1}: {e}{Colors.ENDC}")
                
            await asyncio.sleep(1)
            
        print(f"{Colors.RED}[LỖI] Không thể click Copy Button.{Colors.ENDC}")
        return None
# ========== HỆ THỐNG XỬ LÝ LỆNH WINDOWS ==========
def extract_commands(text):
    """Trích xuất các block code bash/cmd/powershell từ markdown (Hỗ trợ chuẩn Windows \r\n)"""
    # Regex mới: [^\n]* giúp bỏ qua mọi ký tự (như \r hay khoảng trắng thừa) nằm trên cùng dòng với ```powershell
    pattern = r'```(?:powershell|cmd|bat|bash|ps1|pwsh|sh)?[^\n]*\n(.*?)```'
    
    # re.DOTALL giúp dấu chấm (.) bắt được cả ký tự xuống dòng
    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
    
    # Làm sạch khoảng trắng và dòng trống ở đầu/cuối của lệnh
    cleaned_matches = [match.strip() for match in matches if match.strip()]
    
    return cleaned_matches
    """Trích xuất các block code bash/cmd/powershell từ markdown"""
    # Tìm các block ```cmd, ```powershell, ```bat, ```bash
    pattern = r'```(?:powershell|cmd|bat|bash|ps1)\n(.*?)\n```'
    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
    return matches

def execute_windows_command(command):
    """Chạy lệnh bằng PowerShell và bắt Output"""
    print(f"\n{Colors.YELLOW}>>> ĐANG THỰC THI LỆNH:{Colors.ENDC}\n{command}")
    try:
        # Chạy qua powershell để tương thích tốt nhất với các lệnh tạo file
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        out = result.stdout.strip()
        err = result.stderr.strip()
        
        output_log = ""
        if out: output_log += f"STDOUT:\n{out}\n"
        if err: output_log += f"STDERR:\n{err}\n"
        if not out and not err: output_log = "Lệnh chạy thành công, không có output."
        
        print(f"{Colors.CYAN}--- KẾT QUẢ ---{Colors.ENDC}\n{output_log}")
        return output_log
    except Exception as e:
        err_msg = f"Lỗi hệ thống khi chạy lệnh: {e}"
        print(f"{Colors.RED}{err_msg}{Colors.ENDC}")
        return err_msg

# ========== NHẬP DỮ LIỆU TỪ NGƯỜI DÙNG KHÔNG BLOCK ASYNC ==========
async def async_input(prompt_text):
    return await asyncio.to_thread(input, prompt_text)

# ========== VÒNG LẶP AGENT CHÍNH ==========
async def main_agent_loop(initial_prompt):
    agent = DeepSeekAgent()
    await agent.connect()
    
    # 1. GIAI ĐOẠN LẬP KẾ HOẠCH
    system_rules = (
        "Bạn là một Trợ lý Lập trình (Dev Agent) tự động. "
        "QUY TẮC BẮT BUỘC KHI VIẾT FILE HOẶC CHẠY LỆNH (CHO MÔI TRƯỜNG WINDOWS/POWERSHELL):\n"
        "1. Mọi lệnh hệ thống, lệnh tạo file, tạo folder phải đặt gọn trong khối markdown: ```powershell ... ```\n"
        "2. ĐỂ TẠO FILE CHỨA CODE, sử dụng cú pháp PowerShell Heredoc CHUẨN như sau:\n"
        "```powershell\n"
        "$code = @'\n"
        "Nội dung file code của bạn đặt ở đây...\n"
        "'@\n"
        "Set-Content -Path 'ten_file.py' -Value $code -Encoding UTF8\n"
        "```\n"
        "3. Ở giai đoạn này, CHỈ LẬP KẾ HOẠCH chi tiết từng bước. KHÔNG output code/lệnh hệ thống ngay bây giờ."
    )
    
    plan_prompt = f"{system_rules}\n\nYêu cầu dự án của người dùng: {initial_prompt}\n\nHãy lập kế hoạch từng bước rõ ràng để thực hiện."
    
    response = await agent.send_prompt(plan_prompt)
    print(f"\n{Colors.GREEN}{Colors.BOLD}=== KẾ HOẠCH TỪ DEEPSEEK ==={Colors.ENDC}\n{response}\n")
    
    # 2. XÉT DUYỆT KẾ HOẠCH
    while True:
        user_choice = await async_input(f"{Colors.YELLOW}[?] Bạn có đồng ý với kế hoạch này không? (y: Đồng ý & Bắt đầu / q: Thoát / Gõ text để yêu cầu sửa kế hoạch): {Colors.ENDC}")
        user_choice = user_choice.strip()
        
        if user_choice.lower() == 'y':
            print(f"{Colors.CYAN}[HỆ THỐNG] Đã chốt kế hoạch. Chuyển sang giai đoạn Thực thi.{Colors.ENDC}")
            break
        elif user_choice.lower() == 'q':
            sys.exit(0)
        else:
            print(f"{Colors.CYAN}[AGENT] Đang yêu cầu AI lập lại kế hoạch theo góp ý...{Colors.ENDC}")
            revise_prompt = f"Người dùng không đồng ý với kế hoạch. Góp ý của họ: '{user_choice}'. Hãy lập lại kế hoạch mới dựa trên góp ý này."
            response = await agent.send_prompt(revise_prompt)
            print(f"\n{Colors.GREEN}{Colors.BOLD}=== KẾ HOẠCH MỚI ==={Colors.ENDC}\n{response}\n")

    # 3. GIAI ĐOẠN THỰC THI (VÒNG LẶP ITERATIVE)
    current_instruction = "Kế hoạch đã được duyệt. Hãy bắt đầu thực thi BƯỚC ĐẦU TIÊN. Cung cấp lệnh PowerShell trong block ```powershell ... ``` để tạo file/thư mục tương ứng. Chỉ làm bước 1 và đợi kết quả từ tôi."
    
    while True:
        # Gửi yêu cầu bước tiếp theo
        response = await agent.send_prompt(current_instruction)
        print(f"\n{Colors.GREEN}{Colors.BOLD}=== DEEPSEEK TRẢ LỜI ==={Colors.ENDC}\n{response}\n")
        
        # Tìm lệnh Windows trong response
        commands = extract_commands(response)
        
        if commands:
            command_outputs = []
            for idx, cmd in enumerate(commands, 1):
                print(f"\n{Colors.HEADER}=== PHÁT HIỆN LỆNH CẦN THỰC THI ({idx}/{len(commands)}) ==={Colors.ENDC}")
                print(f"{Colors.CYAN}{cmd}{Colors.ENDC}")
                
                # Hỏi ý kiến chạy lệnh
                permit = await async_input(f"{Colors.YELLOW}[?] Cho phép chạy lệnh trên? (y: Chạy / n: Bỏ qua lệnh này / q: Thoát / Gõ lệnh khác để thay thế): {Colors.ENDC}")
                permit = permit.strip()
                
                if permit.lower() == 'y':
                    out = execute_windows_command(cmd)
                    command_outputs.append(f"Lệnh {idx} Output:\n{out}")
                elif permit.lower() == 'n':
                    command_outputs.append(f"Lệnh {idx}: Người dùng đã từ chối chạy lệnh này.")
                    print(f"{Colors.RED}Đã bỏ qua lệnh.{Colors.ENDC}")
                elif permit.lower() == 'q':
                    sys.exit(0)
                else:
                    # User gõ lệnh thủ công thay thế
                    out = execute_windows_command(permit)
                    command_outputs.append(f"Người dùng tự chạy lệnh thay thế ({permit}) Output:\n{out}")
            
            # Gửi output phản hồi lại cho AI để nó làm bước tiếp
            combined_output = "\n".join(command_outputs)
            current_instruction = (
                f"Dưới đây là kết quả sau khi chạy lệnh hệ thống:\n{combined_output}\n\n"
                "Hãy phân tích kết quả trên. Nếu có lỗi, hãy đưa ra lệnh PowerShell sửa lỗi. "
                "Nếu thành công, hãy thực hiện BƯỚC TIẾP THEO trong kế hoạch (Cung cấp lệnh ```powershell nếu cần thiết)."
            )
            
        else:
            # Nếu AI chỉ giải thích mà không đưa ra lệnh hệ thống
            print(f"{Colors.YELLOW}[!] DeepSeek không trả về lệnh hệ thống nào trong bước này.{Colors.ENDC}")
            action = await async_input(f"{Colors.YELLOW}[?] Bạn muốn làm gì tiếp theo? (Nhấn Enter để chuyển sang bước kế tiếp / Gõ yêu cầu mới / q: Thoát): {Colors.ENDC}")
            if action.lower() == 'q':
                sys.exit(0)
            elif action.strip() == '':
                current_instruction = "Hoàn thành. Hãy làm tiếp bước tiếp theo trong kế hoạch. (Nhớ cung cấp lệnh ```powershell nếu cần viết code/tạo file)."
            else:
                current_instruction = action

# ========== ENTRY POINT ==========
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"{Colors.HEADER}{'='*80}\nDEEPSEEK AGENT CLI - AUTO BUILDER\n{'='*80}{Colors.ENDC}")
        print('\n📌 Sử dụng: python agent_deepseek.py "Tạo cho tôi một web server bằng Flask có 2 API..."\n')
        print("⚠️  Đảm bảo Chrome đang chạy với port 9222 (chrome.exe --remote-debugging-port=9222)")
        sys.exit(1)
        
    initial_prompt = " ".join(sys.argv[1:])
    
    try:
        asyncio.run(main_agent_loop(initial_prompt))
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}⚠️ Đã hủy bởi người dùng.{Colors.ENDC}")
        sys.exit(0)
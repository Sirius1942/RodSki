"""测试执行服务 - 调用 RodSki CLI"""
import os
import subprocess
import json
import yaml
from typing import Optional, Dict, List


class RunnerService:
    """测试执行服务"""
    
    def __init__(self, data_path: str = None, config_path: str = None):
        if config_path is None:
            config_path = 'config.yaml'
        
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.rodski_config = self.config['rodski']
        self.project_path = self.rodski_config['project_path']
        # 如果传入了 data_path，优先使用；否则从配置读取
        self.data_path = data_path if data_path else self.rodski_config.get('data_path', '')
        self.run_timeout = self.rodski_config.get('run_timeout', 300)
        
        # RodSki CLI 路径
        self.cli_path = os.path.join(self.project_path, 'cli_main.py')
    
    def run_case(self, case_id: str, case_path: str = None) -> Dict:
        """执行单个测试用例"""
        if case_path is None:
            case_path = self._find_case_path(case_id)
        
        if not case_path:
            return {
                'success': False,
                'error': f'找不到用例: {case_id}'
            }
        
        # 构建命令
        cmd = [
            'python3',
            self.cli_path,
            'run',
            case_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.run_timeout,
                cwd=self.project_path
            )
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'case_id': case_id,
                'case_path': case_path
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'执行超时 ({self.run_timeout}秒)'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_case_dry_run(self, case_id: str) -> Dict:
        """验证用例（不实际执行）"""
        case_path = self._find_case_path(case_id)
        
        if not case_path:
            return {
                'success': False,
                'error': f'找不到用例: {case_id}'
            }
        
        cmd = [
            'python3',
            self.cli_path,
            'run',
            case_path,
            '--dry-run'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_path
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'case_id': case_id
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def explain_case(self, case_id: str) -> Dict:
        """生成用例说明"""
        case_path = self._find_case_path(case_id)
        
        if not case_path:
            return {
                'success': False,
                'error': f'找不到用例: {case_id}'
            }
        
        cmd = [
            'python3',
            self.cli_path,
            'explain',
            case_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_path
            )
            
            return {
                'success': result.returncode == 0,
                'explanation': result.stdout,
                'case_id': case_id
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_batch(self, case_names: List[str]) -> Dict:
        """批量执行测试用例"""
        results = []
        for case_name in case_names:
            result = self.run_case(case_name)
            results.append({
                'case': case_name,
                'result': result
            })
        
        passed = sum(1 for r in results if r['result'].get('success', False))
        failed = len(results) - passed
        
        return {
            'total': len(results),
            'passed': passed,
            'failed': failed,
            'results': results
        }
    
    def _find_case_path(self, case_id: str) -> Optional[str]:
        """查找用例文件路径"""
        if not self.data_path:
            return None
        # 搜索 data_path 下的所有 case 目录
        for root, dirs, files in os.walk(self.data_path):
            for f in files:
                if f.endswith('.xml'):
                    file_path = os.path.join(root, f)
                    # 简单检查文件内容是否包含该 case_id
                    try:
                        with open(file_path, 'r') as fp:
                            if case_id in fp.read():
                                return file_path
                    except:
                        pass
        
        return None
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """获取执行历史"""
        from src.services.result_service import ResultService
        result_service = ResultService(self.data_path)
        return result_service.list_results(limit)
    
    def get_status(self) -> Dict:
        """获取执行器状态"""
        return {
            'project_path': self.project_path,
            'data_path': self.data_path,
            'cli_path': self.cli_path,
            'run_timeout': self.run_timeout,
            'cli_exists': os.path.exists(self.cli_path)
        }

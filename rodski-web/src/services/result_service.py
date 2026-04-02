"""结果服务"""
from typing import List, Dict, Optional
import os
import glob


class ResultService:
    """结果管理服务"""
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            import yaml
            with open('config.yaml') as f:
                config = yaml.safe_load(f)
                data_path = config['rodski']['data_path']
        
        self.data_path = data_path
        self.result_dir = os.path.join(data_path, 'results')
        os.makedirs(self.result_dir, exist_ok=True)
    
    def list_results(self, limit: int = 50) -> List[Dict]:
        """获取结果列表"""
        results = []
        pattern = os.path.join(self.result_dir, '*.xml')
        
        for path in sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)[:limit]:
            result = self._parse_result_file(path)
            if result:
                results.append(result)
        
        return results
    
    def get_result(self, result_name: str) -> Optional[Dict]:
        """获取单个结果"""
        path = os.path.join(self.result_dir, result_name)
        if not path.endswith('.xml'):
            path += '.xml'
        
        if os.path.exists(path):
            return self._parse_result_file(path)
        return None
    
    def _parse_result_file(self, path: str) -> Dict:
        """解析结果文件"""
        import xml.etree.ElementTree as ET
        
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            
            return {
                'name': os.path.basename(path),
                'path': path,
                'status': root.get('status', 'unknown'),
                'passed': root.get('passed', '0'),
                'failed': root.get('failed', '0'),
                'duration': root.get('duration', '0'),
                'timestamp': root.get('timestamp', '')
            }
        except Exception as e:
            return {
                'name': os.path.basename(path),
                'path': path,
                'status': 'error',
                'error': str(e)
            }
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        results = self.list_results(100)
        
        total = len(results)
        passed = sum(1 for r in results if r.get('status') == 'PASS')
        failed = total - passed
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': f"{(passed/total*100) if total > 0 else 0:.1f}%"
        }

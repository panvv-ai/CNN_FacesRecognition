博客地址：https://www.cnblogs.com/panweiwei/

GitHub 地址：https://github.com/panvv-ai/CNN_FacesRecognition

## 环境要求

- Python 3.11+
- 训练和照片识别：`pip install -r requirements.txt`
- 视频/摄像头采集（需要 Dlib）：`pip install -r requirements-face-detection.txt`

## 项目结构

dataset：存放数据集；

MyModel：存放训练的模型文件（运行训练脚本后自动创建）；

model_test：测试模型时，存放待测的照片、视频；

my_faces / MySource_faces：用于测试采集人脸数据集时存放对应数据；

仓库内的示例照片仅用于演示程序流程。使用人脸图片训练或发布模型前，请确认你已获得当事人的明确授权，并遵守所在地的人脸数据处理规定。

## 一：采集人脸数据集

从照片采集：faces_from_Photo.py

从视频文件采集：faces_from_Video.py

从摄像头采集：faces_from_Camera.py

加载照片的函数：read_img.py

## 二：处理照片并加载标签

load_dataset.py

## 三：构建并训练模型

运行 `python train_model.py` 开始训练，模型默认保存到 `./MyModel/model.keras`。

处理数据集的函数：dataSet.py

## 四：模型测试

识别照片中的人脸：Recognize_From_Photo.py

识别视频文件中的人脸：Recognize_From_Vedio.py

识别摄像头中的人脸：Recognize_From_Camera.py

## 本地验证

```bash
python -m unittest discover -s tests -v
```
